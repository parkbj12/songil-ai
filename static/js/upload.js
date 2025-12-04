// 업로드 페이지 전용 JavaScript

// 전역 변수
let currentUserId = '';
let userIdValidated = false;
let userIdCheckInProgress = false;
let userIdValidationTimer = null;
let lastUploadResult = null; // 마지막 업로드 결과 저장

// 특징 이름 한글 변환 함수
function translateFeatureName(englishName) {
    const featureMap = {
        // 활동 관련
        'activity_score_move_every_hour': '매시간 활동 점수',
        'activity_inactive': '비활동 시간',
        'activity_cal_total': '총 활동 칼로리',
        'activity': '활동량',
        'activity_score': '활동 점수',
        'activity_move': '이동 활동',
        'activity_cal': '활동 칼로리',
        
        // 심박수 관련
        'heart_rate': '심박수',
        'heart_rate_avg': '평균 심박수',
        'heart_rate_max': '최대 심박수',
        'heart_rate_min': '최소 심박수',
        'resting_heart_rate': '안정 시 심박수',
        
        // 걸음수 관련
        'steps': '걸음수',
        'step_count': '걸음수',
        'steps_total': '총 걸음수',
        'steps_avg': '평균 걸음수',
        
        // 수면 관련
        'sleep': '수면 시간',
        'sleep_duration': '수면 시간',
        'sleep_total': '총 수면 시간',
        'sleep_deep': '깊은 수면',
        'sleep_light': '얕은 수면',
        'sleep_rem': 'REM 수면',
        
        // 체온 관련
        'temperature': '체온',
        'body_temperature': '체온',
        'temp': '체온',
        
        // 거리 관련
        'distance': '이동 거리',
        'distance_total': '총 이동 거리',
        'distance_walking': '걷기 거리',
        'distance_running': '달리기 거리',
        
        // 기타
        'flights_climbed': '계단 오르기',
        'active_energy': '활동 에너지',
        'basal_energy': '기초 대사량',
    };
    
    // 정확한 매칭
    if (featureMap[englishName]) {
        return featureMap[englishName];
    }
    
    // 부분 매칭 (키워드 기반)
    const lowerName = englishName.toLowerCase();
    
    if (lowerName.includes('heart') || lowerName.includes('심박')) {
        if (lowerName.includes('rate')) return '심박수';
        if (lowerName.includes('resting')) return '안정 시 심박수';
        return '심박수';
    }
    
    if (lowerName.includes('step') || lowerName.includes('걸음')) {
        return '걸음수';
    }
    
    if (lowerName.includes('sleep') || lowerName.includes('수면')) {
        if (lowerName.includes('deep')) return '깊은 수면';
        if (lowerName.includes('light')) return '얕은 수면';
        if (lowerName.includes('rem')) return 'REM 수면';
        return '수면 시간';
    }
    
    if (lowerName.includes('temp') || lowerName.includes('체온')) {
        return '체온';
    }
    
    if (lowerName.includes('activity') || lowerName.includes('활동')) {
        if (lowerName.includes('inactive')) return '비활동 시간';
        if (lowerName.includes('cal')) return '활동 칼로리';
        if (lowerName.includes('score')) return '활동 점수';
        if (lowerName.includes('move')) return '이동 활동';
        return '활동량';
    }
    
    if (lowerName.includes('distance') || lowerName.includes('거리')) {
        return '이동 거리';
    }
    
    if (lowerName.includes('flight') || lowerName.includes('계단')) {
        return '계단 오르기';
    }
    
    if (lowerName.includes('energy') || lowerName.includes('에너지')) {
        if (lowerName.includes('active')) return '활동 에너지';
        if (lowerName.includes('basal')) return '기초 대사량';
        return '에너지';
    }
    
    // 매칭되지 않으면 원본 반환 (하지만 언더스코어를 공백으로 변환)
    return englishName.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
}

// 페이지 로드 시 초기화
document.addEventListener('DOMContentLoaded', function() {
    // 파일 입력 이벤트 리스너
    const fileInput = document.getElementById('health-file-input');
    const fileLabel = document.querySelector('.file-text');
    if (fileInput && fileLabel) {
        fileInput.addEventListener('change', function(e) {
            const file = e.target.files[0];
            if (file) {
                fileLabel.textContent = file.name;
            } else {
                fileLabel.textContent = '파일 선택';
            }
        });
    }
    
    // 초기에는 기능들 비활성화
    disableUploadFeatures();
    
    // 챗봇 입력도 비활성화
    const chatInput = document.getElementById('chat-input');
    const chatBtn = document.getElementById('chat-send-btn');
    if (chatInput) chatInput.disabled = true;
    if (chatBtn) chatBtn.disabled = true;
    
    // 저장된 사용자 ID 불러오기
    const savedUserId = localStorage.getItem('userId');
    if (savedUserId) {
        const userIdInput = document.getElementById('user-id');
        if (userIdInput) {
            userIdInput.value = savedUserId;
            // 자동으로 검증 실행
            setTimeout(() => {
                validateUserId();
            }, 100);
        }
    }
});

// 사용자 ID 검증 (debounce 적용)
async function validateUserId() {
    const userIdInput = document.getElementById('user-id');
    const userId = userIdInput.value.trim();
    const statusDiv = document.getElementById('user-id-status');
    const loadBtn = document.getElementById('load-data-btn');
    const uploadBtn = document.getElementById('upload-btn');
    
    // 이전 타이머 취소
    if (userIdValidationTimer) {
        clearTimeout(userIdValidationTimer);
    }
    
    // 입력이 비어있으면 즉시 처리
    if (!userId) {
        statusDiv.innerHTML = '<span class="status-error">⚠️ 사용자 ID를 입력해주세요</span>';
        userIdValidated = false;
        disableUploadFeatures();
        loadBtn.disabled = true;
        return;
    }
    
    // ID 형식 검증 (영문, 숫자, 언더스코어, 하이픈만 허용)
    if (!/^[a-zA-Z0-9_-]+$/.test(userId)) {
        statusDiv.innerHTML = '<span class="status-error">❌ 사용자 ID는 영문, 숫자, _, - 만 사용 가능합니다</span>';
        userIdValidated = false;
        disableUploadFeatures();
        loadBtn.disabled = true;
        return;
    }
    
    // 최소 길이 검증
    if (userId.length < 3) {
        statusDiv.innerHTML = '<span class="status-error">❌ 사용자 ID는 최소 3자 이상이어야 합니다</span>';
        userIdValidated = false;
        disableUploadFeatures();
        loadBtn.disabled = true;
        return;
    }
    
    // debounce: 500ms 후에 검증 실행
    userIdValidationTimer = setTimeout(async () => {
        // 입력값이 변경되었는지 확인
        const currentInput = document.getElementById('user-id').value.trim();
        if (currentInput !== userId) {
            return;
        }
        
        // 서버에서 사용자 데이터 확인 (기존 사용자인지 확인)
        try {
            const response = await fetch(`/get_user/${userId}?limit=1`);
            const data = await response.json();
            
            if (data.count > 0) {
                // 기존 사용자
                statusDiv.innerHTML = '<span class="status-success">✅ 기존 사용자입니다. 환영합니다!</span>';
            } else {
                // 새 사용자
                statusDiv.innerHTML = '<span class="status-success">✅ 사용 가능한 ID입니다</span>';
            }
        } catch (error) {
            // 에러 발생 시에도 사용 가능으로 처리
            statusDiv.innerHTML = '<span class="status-success">✅ 사용 가능한 ID입니다</span>';
        }
        
        currentUserId = userId;
        userIdValidated = true;
        enableUploadFeatures();
        loadBtn.disabled = false;
        
        // localStorage에 사용자 ID 저장
        localStorage.setItem('userId', userId);
    }, 500);
}

// 사용자 ID 입력 시 Enter 키 처리
function handleUserIdKeyPress(event) {
    if (event.key === 'Enter' && userIdValidated) {
        loadUserData();
    }
}

// 사용자 데이터 조회
async function loadUserData() {
    if (!userIdValidated) {
        showError('먼저 사용자 ID를 입력하고 확인해주세요.');
        return;
    }
    
    const userId = document.getElementById('user-id').value.trim();
    if (!userId) {
        showError('사용자 ID를 입력해주세요.');
        return;
    }
    
    currentUserId = userId;
    alert('데이터 조회 완료!');
}

// 업로드 기능 비활성화
function disableUploadFeatures() {
    const uploadBtn = document.getElementById('upload-btn');
    if (uploadBtn) uploadBtn.disabled = true;
    
    // 챗봇 입력도 비활성화
    const chatInput = document.getElementById('chat-input');
    const chatBtn = document.getElementById('chat-send-btn');
    if (chatInput) chatInput.disabled = true;
    if (chatBtn) chatBtn.disabled = true;
}

// 업로드 기능 활성화
function enableUploadFeatures() {
    const uploadBtn = document.getElementById('upload-btn');
    if (uploadBtn) uploadBtn.disabled = false;
    
    // 챗봇 입력도 활성화
    const chatInput = document.getElementById('chat-input');
    const chatBtn = document.getElementById('chat-send-btn');
    if (chatInput) chatInput.disabled = false;
    if (chatBtn) chatBtn.disabled = false;
}

// 건강 데이터 파일 업로드
async function uploadHealthFile() {
    if (!userIdValidated) {
        showError('먼저 사용자 ID를 입력하고 확인해주세요.');
        return;
    }
    
    const fileInput = document.getElementById('health-file-input');
    const file = fileInput.files[0];
    const userId = document.getElementById('user-id').value.trim();
    const statusDiv = document.getElementById('upload-status');
    const fileLabel = document.querySelector('.file-text');
    
    if (!file) {
        statusDiv.innerHTML = '<p style="color: #ef4444; padding: 10px; background: #fee; border-radius: 8px;">파일을 선택해주세요.</p>';
        return;
    }
    
    if (!userId) {
        showError('사용자 ID를 입력해주세요.');
        return;
    }
    
    // 파일명 표시 업데이트
    if (fileLabel) {
        fileLabel.textContent = file.name;
    }
    
    statusDiv.innerHTML = '<p style="color: #667eea; padding: 10px; background: #e0f2fe; border-radius: 8px;">📤 파일 업로드 중...</p>';
    
    try {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('user_id', userId);
        
        const response = await fetch('/upload_health_data', {
            method: 'POST',
            body: formData
        });
        
        let result;
        try {
            result = await response.json();
        } catch (e) {
            // JSON 파싱 실패 시 텍스트로 읽기
            const text = await response.text();
            statusDiv.innerHTML = `<p style="color: red;">업로드 실패: 서버 응답 오류 (${response.status})</p><p style="font-size: 12px; color: #666;">${text.substring(0, 200)}</p>`;
            console.error('Upload error:', text);
            return;
        }
        
        if (!response.ok || result.error) {
            let errorMsg = result.error || `서버 오류 (${response.status})`;
            
            // 디버깅 정보가 있으면 표시
            if (result.debug_info) {
                const debugInfo = result.debug_info;
                errorMsg += '<br><br><strong>디버깅 정보:</strong><br>';
                errorMsg += `- 루트 요소: ${debugInfo.root_element || 'N/A'}<br>`;
                errorMsg += `- 발견된 요소: ${debugInfo.elements_found ? debugInfo.elements_found.slice(0, 10).join(', ') : 'N/A'}<br>`;
                errorMsg += `- Observation: ${debugInfo.has_observation ? '있음' : '없음'}<br>`;
                errorMsg += `- Entry: ${debugInfo.has_entry ? '있음' : '없음'}<br>`;
                errorMsg += `- Record: ${debugInfo.has_record ? '있음' : '없음'}<br>`;
                errorMsg += `- Section: ${debugInfo.has_section ? '있음' : '없음'}<br>`;
                
                console.log('Debug info:', debugInfo);
            }
            
            statusDiv.innerHTML = `<div style="padding: 15px; background: #fee; border-radius: 8px; border-left: 4px solid #ef4444;"><p style="color: #dc2626; font-weight: 600; margin-bottom: 10px;">❌ 업로드 실패</p><p style="color: #991b1b;">${errorMsg}</p></div>`;
            console.error('Upload error:', result);
            return;
        }
        
        const statusClass = result.anomaly_detected ? 'warning' : 'success';
        const statusBg = result.anomaly_detected ? '#fff3cd' : '#d1fae5';
        const statusColor = result.anomaly_detected ? '#856404' : '#065f46';
        
        // 알림 발송 여부 확인
        let notificationMessage = '';
        if (result.notification) {
            if (result.notification.sent) {
                notificationMessage = `<p style="color: ${statusColor}; margin: 5px 0; font-weight: 500;">📧 알림 발송: ✅ 이메일로 알림이 전송되었습니다.</p>`;
            } else {
                notificationMessage = `<p style="color: #dc2626; margin: 5px 0;">📧 알림 발송: ❌ 실패 (${result.notification.error || '알 수 없는 오류'})</p>`;
            }
        } else if (result.anomaly_detected) {
            notificationMessage = `<p style="color: #666; margin: 5px 0; font-size: 0.9em;">📧 알림: 이상이 감지되었지만 알림 설정이 되어있지 않습니다.</p>`;
        }
        
        statusDiv.innerHTML = `
            <div style="padding: 15px; background: ${statusBg}; border-radius: 8px; border-left: 4px solid ${result.anomaly_detected ? '#f59e0b' : '#10b981'};">
                <p style="color: ${statusColor}; font-weight: 600; margin-bottom: 10px;">✅ 업로드 성공!</p>
                <p style="color: ${statusColor}; margin: 5px 0;">이상 탐지: ${result.anomaly_detected ? '⚠️ 감지됨' : '✅ 정상'}</p>
                <p style="color: ${statusColor}; margin: 5px 0;">이상 점수: ${result.anomaly_score?.toFixed(3) || 'N/A'}</p>
                ${notificationMessage}
            </div>
        `;
        
        // 결과 섹션 표시
        const resultSection = document.getElementById('result-section');
        const resultContainer = document.getElementById('upload-result');
        
        if (resultSection && resultContainer) {
            resultSection.style.display = 'block';
            
            let resultHtml = `
                <div class="result-card">
                    <h3>분석 결과</h3>
                    <div class="result-item">
                        <label>이상 탐지:</label>
                        <span class="value ${result.anomaly_detected ? 'anomaly' : 'normal'}">
                            ${result.anomaly_detected ? '⚠️ 감지됨' : '✅ 정상'}
                        </span>
                    </div>
                    <div class="result-item">
                        <label>이상 점수:</label>
                        <span class="value">${result.anomaly_score?.toFixed(3) || 'N/A'}</span>
                    </div>
                    <div class="result-item">
                        <label>재구성 오차:</label>
                        <span class="value">${result.reconstruction_error?.toFixed(4) || 'N/A'}</span>
                    </div>
                    <div class="result-item">
                        <label>임계값:</label>
                        <span class="value">${result.threshold?.toFixed(4) || 'N/A'}</span>
                    </div>
            `;
            
            // 알림 발송 정보 추가
            if (result.notification) {
                if (result.notification.sent) {
                    resultHtml += `
                        <div class="result-item">
                            <label>알림 발송:</label>
                            <span class="value" style="color: #10b981; font-weight: 600;">✅ 이메일로 전송됨</span>
                        </div>
                    `;
                } else {
                    resultHtml += `
                        <div class="result-item">
                            <label>알림 발송:</label>
                            <span class="value" style="color: #ef4444;">❌ 실패: ${result.notification.error || '알 수 없는 오류'}</span>
                        </div>
                    `;
                }
            } else if (result.anomaly_detected) {
                resultHtml += `
                    <div class="result-item">
                        <label>알림 발송:</label>
                        <span class="value" style="color: #666;">⚠️ 알림 설정이 필요합니다</span>
                    </div>
                `;
            }
            
            resultHtml += `
            `;
            
            if (result.chatbot_feedback) {
                resultHtml += `
                    <div class="result-item full-width">
                        <label>챗봇 피드백:</label>
                        <div class="feedback-text">${result.chatbot_feedback}</div>
                    </div>
                `;
            }
            
            if (result.feature_analysis && result.feature_analysis.top_anomalous_features) {
                resultHtml += `
                    <div class="result-item full-width">
                        <label>주요 이상 특징:</label>
                        <div class="feature-list">
                            ${result.feature_analysis.top_anomalous_features.map(f => {
                                const koreanName = translateFeatureName(f[0]);
                                return `<span class="feature-tag">${koreanName}: ${f[1]?.toFixed(3) || 'N/A'}</span>`;
                            }).join('')}
                        </div>
                    </div>
                `;
            }
            
            resultHtml += '</div>';
            resultContainer.innerHTML = resultHtml;
            
            // 업로드 결과 저장 (저장 버튼용)
            lastUploadResult = result;
            
            // 저장 버튼 표시
            const saveButtonContainer = document.getElementById('save-button-container');
            if (saveButtonContainer) {
                saveButtonContainer.style.display = 'block';
            }
            
            // 결과 섹션으로 스크롤
            setTimeout(() => {
                resultSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }, 300);
        }
        
        // 챗봇 피드백 추가
        console.log('업로드 결과:', result);
        if (result.chatbot_feedback) {
            console.log('챗봇 피드백:', result.chatbot_feedback);
            addChatMessage('bot', result.chatbot_feedback);
            
            // 챗봇 섹션으로 스크롤
            setTimeout(() => {
                scrollToChatbot();
            }, 500);
        } else {
            console.warn('챗봇 피드백이 없습니다. 서버 응답:', result);
            // 피드백이 없어도 기본 메시지 추가
            const defaultMessage = result.anomaly_detected 
                ? '⚠️ 건강 데이터에서 이상 패턴이 감지되었습니다. 건강 상태를 확인해보시기 바랍니다.'
                : '✅ 건강 데이터가 정상 범위 내에 있습니다. 계속해서 건강을 관리해주세요.';
            addChatMessage('bot', defaultMessage);
            setTimeout(() => {
                scrollToChatbot();
            }, 500);
        }
        
    } catch (error) {
        statusDiv.innerHTML = `<div style="padding: 15px; background: #fee; border-radius: 8px; border-left: 4px solid #ef4444;"><p style="color: #dc2626; font-weight: 600;">❌ 업로드 실패: ${error.message}</p></div>`;
    }
}

// 에러 표시
function showError(message) {
    alert('오류: ' + message);
}

// 챗봇 메시지 추가
function addChatMessage(type, message) {
    const messagesContainer = document.getElementById('chat-messages');
    if (!messagesContainer) return;
    
    const messageDiv = document.createElement('div');
    messageDiv.className = `chat-message ${type}`;
    messageDiv.textContent = message;
    messagesContainer.appendChild(messageDiv);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

// 챗봇 메시지 전송
async function sendChatMessage() {
    if (!userIdValidated) {
        showError('먼저 사용자 ID를 입력하고 확인해주세요.');
        return;
    }
    
    const input = document.getElementById('chat-input');
    const message = input.value.trim();
    
    if (!message) return;
    
    // 사용자 메시지 표시
    addChatMessage('user', message);
    input.value = '';
    
    try {
        const userId = document.getElementById('user-id').value.trim();
        const response = await fetch('/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                message: message,
                user_id: userId
            })
        });
        
        const data = await response.json();
        
        if (data.error) {
            addChatMessage('bot', '죄송합니다. 오류가 발생했습니다: ' + data.error);
            return;
        }
        
        // 챗봇 응답 표시
        addChatMessage('bot', data.response);
        
    } catch (error) {
        addChatMessage('bot', '죄송합니다. 연결 오류가 발생했습니다.');
    }
}

// 엔터키 처리
function handleChatKeyPress(event) {
    if (event.key === 'Enter') {
        sendChatMessage();
    }
}

// 챗봇 섹션으로 스크롤
function scrollToChatbot() {
    const chatbotSection = document.querySelector('.chatbot-section');
    if (chatbotSection) {
        chatbotSection.scrollIntoView({ 
            behavior: 'smooth', 
            block: 'start' 
        });
    }
}

// 업로드된 데이터 저장
async function saveUploadedData() {
    if (!lastUploadResult) {
        alert('저장할 데이터가 없습니다. 먼저 파일을 업로드해주세요.');
        return;
    }
    
    if (!userIdValidated) {
        alert('먼저 사용자 ID를 입력하고 확인해주세요.');
        return;
    }
    
    const userId = document.getElementById('user-id').value.trim();
    if (!userId) {
        alert('사용자 ID를 입력해주세요.');
        return;
    }
    
    const saveBtn = document.getElementById('save-uploaded-data-btn');
    const originalText = saveBtn.innerHTML;
    saveBtn.disabled = true;
    saveBtn.innerHTML = '<span style="margin-right: 8px;">⏳</span>저장 중...';
    
    try {
        // 업로드 결과에서 센서 데이터 추출
        // 업로드 API 응답에서 sensor_data를 가져와야 함
        // 만약 업로드 응답에 sensor_data가 없다면, 원본 파일 데이터를 사용해야 할 수도 있음
        
        // 현재 날짜
        const today = new Date().toISOString().split('T')[0];
        
        // 저장할 데이터 구성
        const saveData = {
            user_id: userId,
            date: today,
            sensor_data: lastUploadResult.sensor_data || [], // 업로드 결과에서 센서 데이터 가져오기
            anomaly_score: lastUploadResult.anomaly_score,
            anomaly_detected: lastUploadResult.anomaly_detected,
            chatbot_feedback: lastUploadResult.chatbot_feedback
        };
        
        const response = await fetch('/save_data', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(saveData)
        });
        
        const result = await response.json();
        
        if (result.success) {
            saveBtn.innerHTML = '<span style="margin-right: 8px;">✅</span>저장 완료!';
            saveBtn.style.background = '#10b981';
            
            alert('✅ 데이터가 성공적으로 저장되었습니다!');
            
            // 2초 후 버튼 원래대로
            setTimeout(() => {
                saveBtn.innerHTML = originalText;
                saveBtn.style.background = '';
                saveBtn.disabled = false;
            }, 2000);
        } else {
            throw new Error(result.error || '저장 실패');
        }
        
    } catch (error) {
        console.error('저장 실패:', error);
        alert('❌ 저장 중 오류가 발생했습니다: ' + error.message);
        saveBtn.innerHTML = originalText;
        saveBtn.disabled = false;
    }
}

