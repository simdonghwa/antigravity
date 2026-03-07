'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import styles from './login.module.css';
import { Lock, Smartphone, Building2 } from 'lucide-react';

export default function LoginPage() {
    const router = useRouter();
    const [bizNo, setBizNo] = useState('');

    const handleLogin = (e: React.FormEvent) => {
        e.preventDefault();
        // In a real app, validation logic would go here
        if (bizNo.length >= 10) {
            router.push('/home');
        } else {
            alert('올바른 사업자등록번호를 입력해주세요.');
        }
    };

    return (
        <div className={styles.container}>
            <header className={styles.header}>
                <h1 className={styles.title}>로그인</h1>
                <p className={styles.subtitle}>
                    안전한 서비스 이용을 위해<br />
                    사업자 정보를 입력해주세요.
                </p>
            </header>

            <form className={styles.form} onSubmit={handleLogin}>
                <div className={styles.inputGroup}>
                    <label className={styles.label}>사업자등록번호</label>
                    <div className={styles.inputWrapper}>
                        <Building2 className={styles.icon} size={20} />
                        <input
                            type="text"
                            className={styles.input}
                            placeholder="000-00-00000"
                            value={bizNo}
                            onChange={(e) => setBizNo(e.target.value)}
                            maxLength={12}
                        />
                    </div>
                </div>

                <div className={styles.inputGroup}>
                    <label className={styles.label}>휴대전화번호</label>
                    <div className={styles.inputWrapper}>
                        <Smartphone className={styles.icon} size={20} />
                        <input
                            type="tel"
                            className={styles.input}
                            placeholder="010-0000-0000"
                        />
                    </div>
                </div>

                <button type="submit" className={styles.submitButton}>
                    <Lock size={18} style={{ marginRight: 8 }} />
                    인증하고 시작하기
                </button>
            </form>
        </div>
    );
}
