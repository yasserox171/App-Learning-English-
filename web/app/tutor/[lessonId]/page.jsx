'use client';

import { useEffect, useRef, useState } from 'react';
import { useParams } from 'next/navigation';
import { api } from '../../../lib/api';

/**
 * AI Tutor voice conversation in the browser (v2 §3 + §8).
 *
 * Safari notes: getUserMedia only resolves from a user gesture on a secure
 * origin, it does not support audio/webm (we fall back to audio/mp4), and
 * autoplay of the reply audio is blocked unless play() is triggered inside
 * the same gesture chain — so the first tap primes a silent <audio> element.
 */
function pickMimeType() {
  if (typeof MediaRecorder === 'undefined') return '';
  const candidates = [
    'audio/webm;codecs=opus',
    'audio/webm',
    'audio/mp4', // Safari
    'audio/ogg;codecs=opus',
  ];
  return candidates.find((type) => MediaRecorder.isTypeSupported(type)) || '';
}

export default function TutorPage() {
  const { lessonId } = useParams();
  const [session, setSession] = useState(null);
  const [turns, setTurns] = useState([]);
  const [recording, setRecording] = useState(false);
  const [busy, setBusy] = useState(false);
  const [ended, setEnded] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');

  const recorderRef = useRef(null);
  const chunksRef = useRef([]);
  const streamRef = useRef(null);
  const audioRef = useRef(null);
  const primedRef = useRef(false);

  useEffect(() => {
    api
      .tutorStart(lessonId)
      .then((data) => {
        setSession(data);
        setTurns([{ role: 'assistant', text: data.opening_text }]);
        if (data.opening_audio_b64) play(data.opening_audio_b64);
      })
      .catch((err) =>
        setError(
          err.status === 429
            ? 'وصلت للحد اليومي لجلسات المدرّس الذكي. عد غداً!'
            : 'تعذّر بدء الجلسة.'
        )
      );
    return () => streamRef.current?.getTracks().forEach((t) => t.stop());
  }, [lessonId]);

  function play(b64) {
    if (!audioRef.current) return;
    audioRef.current.src = `data:audio/mpeg;base64,${b64}`;
    audioRef.current.play().catch(() => {
      /* autoplay blocked — the reply text is always shown */
    });
  }

  async function startRecording() {
    // Prime the audio element inside the user gesture so Safari lets us
    // play the tutor's reply later.
    if (!primedRef.current && audioRef.current) {
      audioRef.current.play().catch(() => {});
      audioRef.current.pause();
      primedRef.current = true;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;
      const mimeType = pickMimeType();
      const recorder = new MediaRecorder(stream, mimeType ? { mimeType } : {});
      chunksRef.current = [];
      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };
      recorder.onstop = () => {
        const blob = new Blob(chunksRef.current, {
          type: mimeType || 'audio/webm',
        });
        stream.getTracks().forEach((t) => t.stop());
        sendTurn(blob);
      };
      recorder.start();
      recorderRef.current = recorder;
      setRecording(true);
    } catch {
      setError('لم نتمكن من الوصول إلى الميكروفون. تحقّق من أذونات المتصفح.');
    }
  }

  function stopRecording() {
    recorderRef.current?.stop();
    setRecording(false);
  }

  async function sendTurn(blob) {
    if (!session || ended) return;
    setBusy(true);
    try {
      const data = await api.tutorTurnAudio(session.session_id, blob);
      setTurns((prev) => [
        ...prev,
        { role: 'user', text: data.transcript },
        { role: 'assistant', text: data.reply_text },
      ]);
      if (data.reply_audio_b64) play(data.reply_audio_b64);
      if (data.ended) finish();
    } catch (err) {
      setError(
        err.status === 400
          ? 'لم نسمع صوتاً واضحاً — حاول مرة أخرى.'
          : 'تعذّر إرسال الرسالة.'
      );
    } finally {
      setBusy(false);
    }
  }

  async function finish() {
    if (!session) return;
    try {
      const data = await api.tutorEnd(session.session_id);
      setResult(data);
      setEnded(true);
    } catch {
      setEnded(true);
    }
  }

  if (error && !session) return <div className="empty">{error}</div>;
  if (!session) return <div className="spinner" />;

  return (
    <>
      <h1 className="page">🎙️ المدرّس الذكي</h1>
      <p className="sub">
        محادثة صوتية قصيرة حول الدرس — حاول استخدام الكلمات المستهدفة.
      </p>

      <div className="vocab-chips">
        {(session.target_vocabulary || []).map((word) => (
          <span className="badge" key={word} dir="ltr">
            {word}
          </span>
        ))}
      </div>

      <div className="card">
        <div className="bubbles">
          {turns.map((turn, i) => (
            <div className={`bubble ${turn.role}`} key={i}>
              {turn.text}
            </div>
          ))}
          {busy && <div className="bubble assistant">…</div>}
        </div>

        {!ended && (
          <div style={{ textAlign: 'center' }}>
            <button
              className={`mic${recording ? ' recording' : ''}`}
              disabled={busy}
              onClick={recording ? stopRecording : startRecording}
            >
              {recording ? '■' : '🎤'}
            </button>
            <p className="sub" style={{ marginTop: 10 }}>
              {recording ? 'جارٍ الاستماع… اضغط للإيقاف' : 'اضغط للتحدث'}
            </p>
            <button className="btn ghost" onClick={finish}>
              إنهاء الجلسة
            </button>
          </div>
        )}

        {result && (
          <div style={{ textAlign: 'center' }}>
            <h3>🎉 انتهت الجلسة</h3>
            <p>
              الكلمات المستهدفة التي استخدمتها:{' '}
              <strong>
                {result.terms_used} / {result.terms_total}
              </strong>
            </p>
          </div>
        )}

        {error && <p className="badge bad">{error}</p>}
      </div>

      {/* eslint-disable-next-line jsx-a11y/media-has-caption */}
      <audio ref={audioRef} hidden />
    </>
  );
}
