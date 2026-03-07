'use client';

import { useState } from 'react';
import Link from 'next/link';
import styles from './home.module.css';
import { Bell, ChevronRight, TrendingUp, Users, ArrowUp, Lock, FileText } from 'lucide-react';

export default function HomePage() {
    const [isVerified, setIsVerified] = useState(false); // Mock state: false = document needed

    return (
        <div className={styles.container}>
            {/* Header */}
            <header className={styles.header}>
                <div>
                    <h1 className={styles.greeting}>안녕하세요,</h1>
                    <h2 className={styles.ceoName}><span className={styles.highlight}>앤티그래비티</span> 사장님!</h2>
                </div>
                <button className={styles.netibtn}>
                    <Bell size={24} color="#1a2b4b" />
                    <span className={styles.badge} />
                </button>
            </header>

            {/* Monthly Insight Dashboard */}
            <section className={styles.dashboard}>
                <div className={styles.card}>
                    <div className={styles.cardHeader}>
                        <span className={styles.cardTitle}>평균 월매출</span>
                        <TrendingUp size={16} className={styles.trendIcon} />
                    </div>
                    <div className={styles.cardValue}>4,520만원</div>
                    <div className={styles.changeRate}>
                        <ArrowUp size={14} />
                        <span>지난달보다 12% 늘었어요</span>
                    </div>
                </div>

                <div className={styles.row}>
                    <div className={styles.halfCard}>
                        <div className={styles.cardHeader}><span className={styles.cardTitle}>재방문율</span></div>
                        <div className={styles.cardValue}>32.5%</div>
                    </div>
                    <div className={styles.halfCard}>
                        <div className={styles.cardHeader}><span className={styles.cardTitle}>단골 손님</span></div>
                        <div className={styles.cardValue}>142명</div>
                    </div>
                </div>
            </section>

            {/* Content Feed */}
            <section className={styles.feed}>
                <div className={styles.tabs}>
                    <button className={`${styles.tab} ${styles.active}`}>주간 동향</button>
                    <button className={styles.tab}>지원사업</button>
                </div>

                <div className={styles.list}>
                    {/* Unlocked Content */}
                    <div className={styles.listItem}>
                        <div className={styles.itemText}>
                            <h3 className={styles.itemTitle}>2024년 1월 3주차 소상공인 주간 브리핑</h3>
                            <p className={styles.itemDesc}>이번 주 놓치면 안 되는 정책 자금 소식을 정리해드려요.</p>
                            <span className={styles.date}>2024.01.17</span>
                        </div>
                    </div>

                    {/* Locked Content (Example) */}
                    <div className={`${styles.listItem} ${!isVerified ? styles.locked : ''}`}>
                        {!isVerified && (
                            <div className={styles.lockOverlay}>
                                <Lock size={24} className={styles.lockIcon} />
                                <p>서류를 제출하고<br />전체 내용을 확인하세요</p>
                                <Link href="/document" className={styles.submitBtn}>서류 제출하기</Link>
                            </div>
                        )}
                        <div className={styles.itemText}>
                            <h3 className={styles.itemTitle}>우리 동네 뜨는 상권 분석 리포트</h3>
                            <p className={styles.itemDesc}>사장님 매장 주변 유동인구와 매출 데이터를 분석했어요.</p>
                            <span className={styles.date}>2024.01.15</span>
                        </div>
                    </div>
                </div>
            </section>

            {/* Bottom Nav Mock */}
            <nav className={styles.bottomNav}>
                <div className={`${styles.navItem} ${styles.navActive}`}>홈</div>
                <div className={styles.navItem}>리포트</div>
                <Link href="/ax" className={styles.navItem} style={{ color: '#3b82f6', fontWeight: 700 }}>AI 자동화</Link>
                <div className={styles.navItem}>내 정보</div>
            </nav>
        </div>
    );
}
