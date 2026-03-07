'use client';

import { useState, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { Upload, FileText, Check, AlertCircle, X, ChevronLeft } from 'lucide-react';
import styles from './document.module.css';

export default function DocumentPage() {
    const router = useRouter();
    const fileInputRef1 = useRef<HTMLInputElement>(null);
    const fileInputRef2 = useRef<HTMLInputElement>(null);

    const [files, setFiles] = useState<{
        bizReg: File | null;
        account: File | null;
    }>({ bizReg: null, account: null });

    // Mock OCR Recognition State
    const [isAnalyzing, setIsAnalyzing] = useState(false);
    const [ocrResult, setOcrResult] = useState<{
        bizNo: string;
        owner: string;
        accountNo: string;
        bankName: string;
    } | null>(null);

    const handleFileSelect = (type: 'bizReg' | 'account', e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files && e.target.files[0]) {
            setFiles(prev => ({ ...prev, [type]: e.target.files![0] }));
        }
    };

    const handleSubmit = async () => {
        if (!files.bizReg || !files.account) return;

        setIsAnalyzing(true);
        // Simulation of Google Apps Script OCR delay
        setTimeout(() => {
            setIsAnalyzing(false);
            setOcrResult({
                bizNo: '123-45-67890',
                owner: '김대표',
                bankName: '우리은행',
                accountNo: '1002-123-456789'
            });
        }, 2000);
    };

    const handleFinalConfirm = () => {
        alert('서류 제출이 완료되었습니다.\n관리자 승인 후 알림을 보내드립니다.');
        router.push('/home');
    };

    return (
        <div className={styles.container}>
            <header className={styles.header}>
                <button onClick={() => router.back()} className={styles.backBtn}>
                    <ChevronLeft size={24} />
                </button>
                <h1 className={styles.title}>서류 제출</h1>
            </header>

            {!ocrResult ? (
                <>
                    <div className={styles.guide}>
                        <h2 className={styles.guideTitle}>
                            서비스 이용을 위해<br />
                            필수 서류를 제출해주세요.
                        </h2>
                        <p className={styles.guideSub}>
                            사업자등록증과 계좌사본을 업로드하면<br />
                            자동으로 정보를 읽어옵니다.
                        </p>
                    </div>

                    <div className={styles.uploadSection}>
                        {/* Business Registration */}
                        <div className={styles.uploadCard} onClick={() => fileInputRef1.current?.click()}>
                            <input
                                type="file"
                                hidden
                                ref={fileInputRef1}
                                accept="image/*,.pdf"
                                onChange={(e) => handleFileSelect('bizReg', e)}
                            />
                            <div className={styles.cardIcon}>
                                {files.bizReg ? <Check size={24} color="#10b981" /> : <FileText size={24} />}
                            </div>
                            <div className={styles.cardText}>
                                <h3>사업자등록증</h3>
                                <p>{files.bizReg ? files.bizReg.name : '터치하여 업로드'}</p>
                            </div>
                            <div className={styles.uploadBadge}>
                                <Upload size={16} />
                            </div>
                        </div>

                        {/* Account Copy */}
                        <div className={styles.uploadCard} onClick={() => fileInputRef2.current?.click()}>
                            <input
                                type="file"
                                hidden
                                ref={fileInputRef2}
                                accept="image/*,.pdf"
                                onChange={(e) => handleFileSelect('account', e)}
                            />
                            <div className={styles.cardIcon}>
                                {files.account ? <Check size={24} color="#10b981" /> : <FileText size={24} />}
                            </div>
                            <div className={styles.cardText}>
                                <h3>계좌사본 (통장사본)</h3>
                                <p>{files.account ? files.account.name : '터치하여 업로드'}</p>
                            </div>
                            <div className={styles.uploadBadge}>
                                <Upload size={16} />
                            </div>
                        </div>
                    </div>

                    <div className={styles.noticeBox}>
                        <AlertCircle size={16} className={styles.noticeIcon} />
                        <p>선명한 이미지를 올려주세요. 흐릿하면 반려될 수 있습니다.</p>
                    </div>

                    <button
                        className={styles.submitBtn}
                        disabled={!files.bizReg || !files.account || isAnalyzing}
                        onClick={handleSubmit}
                    >
                        {isAnalyzing ? '분석 중입니다...' : '다음 내용을 확인'}
                    </button>
                </>
            ) : (
                <div className={styles.confirmSection}>
                    <h2 className={styles.guideTitle}>정보가 올바른지 확인해주세요</h2>

                    <div className={styles.resultCard}>
                        <div className={styles.field}>
                            <label>대표자명</label>
                            <input type="text" defaultValue={ocrResult.owner} className={styles.input} />
                        </div>
                        <div className={styles.field}>
                            <label>사업자번호</label>
                            <input type="text" defaultValue={ocrResult.bizNo} className={styles.input} />
                        </div>
                        <div className={styles.divider} />
                        <div className={styles.field}>
                            <label>은행명</label>
                            <input type="text" defaultValue={ocrResult.bankName} className={styles.input} />
                        </div>
                        <div className={styles.field}>
                            <label>계좌번호</label>
                            <input type="text" defaultValue={ocrResult.accountNo} className={styles.input} />
                        </div>
                    </div>

                    <div className={styles.actions}>
                        <button className={styles.retryBtn} onClick={() => setOcrResult(null)}>
                            다시 올리기
                        </button>
                        <button className={styles.confirmBtn} onClick={handleFinalConfirm}>
                            제출하기
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
}
