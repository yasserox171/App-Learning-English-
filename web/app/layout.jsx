import './globals.css';
import Header from '../components/Header';
import { SessionProvider } from '../components/SessionProvider';

export const metadata = {
  title: 'Focus Languages — تعلّم الإنجليزية',
  description:
    'تعلّم الإنجليزية من A1 إلى C2 مع أخبار مبسّطة ومدرّس ذكي بالمحادثة الصوتية.',
};

export default function RootLayout({ children }) {
  return (
    <html lang="ar" dir="rtl">
      <body>
        <SessionProvider>
          <Header />
          <div className="container">{children}</div>
        </SessionProvider>
      </body>
    </html>
  );
}
