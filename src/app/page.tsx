import Link from 'next/link';
import styles from './page.module.css';

export default function LandingPage() {
  return (
    <main className={styles.container}>
      <div className={styles.hero}>
        <div className={styles.logo}>CheckPoint</div>
        <h1 className={styles.title}>
          사장님의 사업이<br />
          <span className={styles.highlight}>더 가벼워지는</span> 순간
        </h1>
        <p className={styles.subtitle}>
          매출 분석, 지원사업 매칭, 정기 리포트까지.<br />
          복잡한 경영 관리를 한 곳에서 해결하세요.
        </p>
      </div>

      <div className={styles.actions}>
        <Link href="/login" className={styles.primaryButton}>
          시작하기
        </Link>
        <div className={styles.loginInfo}>
          이미 계정이 있으신가요? <Link href="/login"><b>로그인</b></Link>
        </div>
      </div>
    </main>
  );
}
