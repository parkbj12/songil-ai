// 메인 JavaScript 파일

// 전역 변수
let currentUserId = '';
let userData = null;
let timeSeriesData = [];
let userIdValidated = false;
let userIdCheckInProgress = false;
let userIdValidationTimer = null;

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
    // 건강 팁 표시
    showHealthTip();
    
    // 일일 건강 체크 리마인더 설정
    setupDailyReminder();
    // 차트 컨테이너 확인 및 초기화
    initializeCharts();
    
    // 초기에는 기능들 비활성화
    disableAllFeatures();
    
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
    
    // 서버 시작 후 30분 뒤에 첫 알림 확인
    setTimeout(function() {
        checkNotifications();
    }, 30 * 60 * 1000); // 30분 후
    
    // 창 크기 변경 시 차트 자동 조정
    let resizeTimer;
    window.addEventListener('resize', function() {
        clearTimeout(resizeTimer);
        resizeTimer = setTimeout(function() {
            if (document.getElementById('timeseries-chart')) {
                Plotly.Plots.resize('timeseries-chart');
            }
            if (document.getElementById('anomaly-chart')) {
                Plotly.Plots.resize('anomaly-chart');
            }
        }, 250);
    });
    
    // 5분마다 알림 확인 (첫 알림 확인 후부터 시작)
    setTimeout(function() {
        setInterval(checkNotifications, 5 * 60 * 1000);
    }, 30 * 60 * 1000); // 30분 후부터 주기적으로 확인
});

// 차트 초기화
function initializeCharts() {
    // Plotly 라이브러리 로드 확인
    if (typeof Plotly === 'undefined') {
        console.error('Plotly 라이브러리가 로드되지 않았습니다.');
        const timeSeriesContainer = document.getElementById('timeseries-chart');
        const anomalyContainer = document.getElementById('anomaly-chart');
        
        if (timeSeriesContainer) {
            timeSeriesContainer.innerHTML = '<div class="chart-error">Plotly 라이브러리를 로드할 수 없습니다. 인터넷 연결을 확인해주세요.</div>';
        }
        if (anomalyContainer) {
            anomalyContainer.innerHTML = '<div class="chart-error">Plotly 라이브러리를 로드할 수 없습니다. 인터넷 연결을 확인해주세요.</div>';
        }
        return;
    }
    
    // 시계열 차트 초기화 (history 페이지에서만)
    const timeSeriesContainer = document.getElementById('timeseries-chart');
    if (timeSeriesContainer) {
        updateTimeSeriesChart([]); // 빈 데이터로 초기화
    }
    
    // 이상 탐지 차트 초기화 (history 페이지에서만)
    const anomalyContainer = document.getElementById('anomaly-chart');
    if (anomalyContainer) {
        // 빈 차트로 초기화
        try {
            const emptyTrace = {
                x: [new Date().toLocaleString('ko-KR')],
                y: [0],
                type: 'scatter',
                mode: 'lines+markers',
                name: '이상 점수',
                line: { color: '#667eea' }
            };
            
            const emptyLayout = {
                title: {
                    text: '이상 탐지 점수',
                    font: { size: 16, color: '#333', family: 'Arial, sans-serif' }
                },
                xaxis: { 
                    title: { text: '시간', font: { size: 12 } },
                    showgrid: true,
                    gridcolor: '#e0e0e0',
                    gridwidth: 1
                },
                yaxis: { 
                    title: { text: '이상 점수', font: { size: 12 } },
                    showgrid: true,
                    gridcolor: '#e0e0e0',
                    gridwidth: 1
                },
                hovermode: 'closest',
                showlegend: true,
                autosize: true,
                margin: { l: 50, r: 40, t: 50, b: 50 },
                height: 400,
                plot_bgcolor: 'rgba(0,0,0,0)',
                paper_bgcolor: 'rgba(0,0,0,0)'
            };
            
            const emptyConfig = {
                responsive: true,
                displayModeBar: true,
                displaylogo: false,
                autosizable: true
            };
            
            Plotly.newPlot('anomaly-chart', [emptyTrace], emptyLayout, emptyConfig);
        } catch (error) {
            console.error('이상 탐지 차트 초기화 실패:', error);
        }
    }
}

// 사용자 ID 검증 (debounce 적용)
async function validateUserId() {
    const userIdInput = document.getElementById('user-id');
    const userId = userIdInput.value.trim();
    const statusDiv = document.getElementById('user-id-status');
    const loadBtn = document.getElementById('load-data-btn');
    
    // 이전 타이머 취소
    if (userIdValidationTimer) {
        clearTimeout(userIdValidationTimer);
    }
    
    // 입력이 비어있으면 즉시 처리
    if (!userId) {
        statusDiv.innerHTML = '<span class="status-error">⚠️ 사용자 ID를 입력해주세요</span>';
        userIdValidated = false;
        disableAllFeatures();
        loadBtn.disabled = true;
        return;
    }
    
    // ID 형식 검증 (영문, 숫자, 언더스코어, 하이픈만 허용)
    if (!/^[a-zA-Z0-9_-]+$/.test(userId)) {
        statusDiv.innerHTML = '<span class="status-error">❌ 사용자 ID는 영문, 숫자, _, - 만 사용 가능합니다</span>';
        userIdValidated = false;
        disableAllFeatures();
        loadBtn.disabled = true;
        return;
    }
    
    // 최소 길이 검증
    if (userId.length < 3) {
        statusDiv.innerHTML = '<span class="status-error">❌ 사용자 ID는 최소 3자 이상이어야 합니다</span>';
        userIdValidated = false;
        disableAllFeatures();
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
        enableAllFeatures();
        loadBtn.disabled = false;
        
        // localStorage에 사용자 ID 저장
        localStorage.setItem('userId', userId);
        
        // 이메일 로드
        loadNotificationEmail();
        loadEmergencyContacts();
        
        // 오늘의 건강 상태 요약 업데이트
        setTimeout(() => {
            updateTodayHealthSummary();
            loadHealthGoals();
            updateGoalProgress();
        }, 1000);
    }, 500);
}

// 건강 팁 데이터
const healthTips = [
    "💚 규칙적인 산책은 심혈관 건강에 도움이 됩니다. 하루 30분씩만 걸어도 큰 효과가 있어요!",
    "😴 충분한 수면은 건강의 기본입니다. 하루 7-8시간의 수면을 권장합니다.",
    "💧 하루에 물을 8잔 이상 마시는 것이 좋습니다. 수분 섭취는 신진대사를 활발하게 합니다.",
    "🍎 아침 식사를 거르지 마세요. 규칙적인 식사는 건강 유지에 중요합니다.",
    "🧘 가벼운 스트레칭을 하루에 10분씩 하면 근육과 관절 건강에 도움이 됩니다.",
    "☀️ 햇빛을 쬐면 비타민 D가 생성되어 뼈 건강에 좋습니다. 하루 15분 정도면 충분해요!",
    "📱 스마트폰 사용 시간을 줄이고 눈을 자주 깜빡이면 눈 건강에 도움이 됩니다.",
    "🚶 계단을 이용하면 심폐 기능 향상에 도움이 됩니다. 엘리베이터 대신 계단을 이용해보세요!",
    "🍵 녹차나 허브차를 마시면 항산화 효과가 있어 건강에 좋습니다.",
    "🎵 좋아하는 음악을 들으며 가벼운 운동을 하면 기분도 좋아지고 건강도 챙길 수 있어요!",
    "🌙 잠들기 1시간 전에는 스마트폰 사용을 줄이면 수면의 질이 향상됩니다.",
    "🥗 채소와 과일을 충분히 섭취하면 면역력 향상에 도움이 됩니다.",
    "💪 근력 운동을 주 2-3회 하면 근육량 유지와 골밀도 향상에 도움이 됩니다.",
    "🧠 독서나 퍼즐 같은 두뇌 활동을 하면 인지 기능 유지에 도움이 됩니다.",
    "🤝 가족이나 친구들과 정기적으로 만나면 정신 건강에 도움이 됩니다.",
    "🌿 실내 공기를 자주 환기시키면 호흡기 건강에 좋습니다.",
    "🍌 바나나나 견과류 같은 간식을 먹으면 에너지를 유지하는 데 도움이 됩니다.",
    "🚴 자전거 타기나 수영 같은 저강도 운동은 관절에 부담을 주지 않으면서 건강을 챙길 수 있어요!",
    "📅 건강 체크를 매일 같은 시간에 하면 더 정확한 분석이 가능합니다.",
    "💤 낮잠을 20-30분 정도 자면 피로 회복에 도움이 되지만, 너무 길게 자면 밤잠에 영향을 줄 수 있어요."
];

let currentTipIndex = 0;

// 건강 팁 표시
function showHealthTip() {
    const tipContent = document.getElementById('health-tip-content');
    if (!tipContent) return;
    
    // 오늘 날짜를 기반으로 팁 선택 (매일 같은 팁)
    const today = new Date();
    const dayOfYear = Math.floor((today - new Date(today.getFullYear(), 0, 0)) / 1000 / 60 / 60 / 24);
    currentTipIndex = dayOfYear % healthTips.length;
    
    tipContent.textContent = healthTips[currentTipIndex];
}

// 다음 팁 보기
function showNextTip() {
    currentTipIndex = (currentTipIndex + 1) % healthTips.length;
    const tipContent = document.getElementById('health-tip-content');
    if (tipContent) {
        tipContent.textContent = healthTips[currentTipIndex];
    }
}

// 건강 목표 저장
let healthGoals = {
    steps: null,
    sleep: null
};

// 건강 목표 로드
function loadHealthGoals() {
    const userId = document.getElementById('user-id').value.trim();
    if (!userId) return;
    
    const savedGoals = localStorage.getItem(`health_goals_${userId}`);
    if (savedGoals) {
        try {
            healthGoals = JSON.parse(savedGoals);
            if (healthGoals.steps) {
                document.getElementById('steps-goal').value = healthGoals.steps;
                document.getElementById('steps-goal-display').textContent = healthGoals.steps.toLocaleString() + '걸음';
            }
            if (healthGoals.sleep) {
                document.getElementById('sleep-goal').value = healthGoals.sleep;
                document.getElementById('sleep-goal-display').textContent = healthGoals.sleep + '시간';
            }
            
            // 목표 섹션 표시
            document.getElementById('health-goals-section').style.display = 'block';
        } catch (e) {
            console.error('목표 로드 실패:', e);
        }
    }
}

// 건강 목표 저장
function saveGoal(type) {
    const userId = document.getElementById('user-id').value.trim();
    if (!userId) {
        alert('먼저 사용자 ID를 입력해주세요.');
        return;
    }
    
    let goalValue;
    let displayElement;
    let displayText;
    
    if (type === 'steps') {
        goalValue = parseInt(document.getElementById('steps-goal').value);
        displayElement = document.getElementById('steps-goal-display');
        displayText = '걸음';
    } else if (type === 'sleep') {
        goalValue = parseFloat(document.getElementById('sleep-goal').value);
        displayElement = document.getElementById('sleep-goal-display');
        displayText = '시간';
    }
    
    if (!goalValue || goalValue <= 0) {
        alert('올바른 목표 값을 입력해주세요.');
        return;
    }
    
    healthGoals[type] = goalValue;
    localStorage.setItem(`health_goals_${userId}`, JSON.stringify(healthGoals));
    
    if (displayElement) {
        displayElement.textContent = type === 'steps' 
            ? goalValue.toLocaleString() + displayText 
            : goalValue + displayText;
    }
    
    // 목표 섹션 표시
    document.getElementById('health-goals-section').style.display = 'block';
    
    // 진행률 업데이트
    updateGoalProgress();
    
    alert('✅ 목표가 저장되었습니다!');
}

// 목표 진행률 업데이트
function updateGoalProgress() {
    const userId = document.getElementById('user-id').value.trim();
    if (!userId || !userIdValidated) return;
    
    // 오늘 날짜
    const today = new Date().toISOString().split('T')[0];
    
    // 오늘 데이터 조회
    fetch(`/get_user/${userId}?date=${today}&limit=1`)
        .then(response => response.json())
        .then(data => {
            if (data.data && data.data.length > 0) {
                const todayData = data.data[0];
                
                // 걸음수 목표 진행률
                if (healthGoals.steps && todayData.sensor_data && todayData.sensor_data.length > 0) {
                    const todaySteps = todayData.sensor_data.reduce((sum, sd) => sum + (sd.steps || 0), 0);
                    const stepsProgress = Math.min(100, (todaySteps / healthGoals.steps) * 100);
                    const stepsBar = document.getElementById('steps-progress-bar');
                    if (stepsBar) {
                        stepsBar.style.width = stepsProgress + '%';
                        stepsBar.textContent = Math.round(stepsProgress) + '%';
                    }
                }
                
                // 수면 목표 진행률
                if (healthGoals.sleep && todayData.sensor_data && todayData.sensor_data.length > 0) {
                    const todaySleep = todayData.sensor_data.reduce((sum, sd) => sum + (sd.sleep || 0), 0) / todayData.sensor_data.length;
                    const sleepProgress = Math.min(100, (todaySleep / healthGoals.sleep) * 100);
                    const sleepBar = document.getElementById('sleep-progress-bar');
                    if (sleepBar) {
                        sleepBar.style.width = sleepProgress + '%';
                        sleepBar.textContent = Math.round(sleepProgress) + '%';
                    }
                }
            }
        })
        .catch(error => {
            console.error('목표 진행률 업데이트 실패:', error);
        });
}

// 일일 건강 체크 리마인더 설정
function setupDailyReminder() {
    // 사용자가 설정한 리마인더 시간 (기본: 오후 2시)
    const reminderTime = localStorage.getItem('daily_reminder_time') || '14:00';
    const [hours, minutes] = reminderTime.split(':').map(Number);
    
    function checkReminder() {
        const now = new Date();
        const currentHour = now.getHours();
        const currentMinute = now.getMinutes();
        
        // 설정된 시간이면 리마인더 표시
        if (currentHour === hours && currentMinute === minutes) {
            const today = new Date().toISOString().split('T')[0];
            const userId = localStorage.getItem('userId');
            
            if (userId) {
                // 오늘 체크했는지 확인
                fetch(`/get_user/${userId}?date=${today}&limit=1`)
                    .then(response => response.json())
                    .then(data => {
                        if (!data.data || data.data.length === 0) {
                            // 오늘 체크 안 했으면 리마인더 표시
                            showDailyReminder();
                        }
                    })
                    .catch(error => console.error('리마인더 확인 실패:', error));
            }
        }
    }
    
    // 1분마다 확인
    setInterval(checkReminder, 60000);
    
    // 브라우저 알림 권한 요청
    if ('Notification' in window && Notification.permission === 'default') {
        Notification.requestPermission();
    }
}

// 일일 건강 체크 리마인더 표시
function showDailyReminder() {
    // 브라우저 알림
    if ('Notification' in window && Notification.permission === 'granted') {
        new Notification('💚 오늘의 건강 체크 시간입니다!', {
            body: '건강 상태를 체크하고 저장해주세요.',
            icon: '/static/favicon.ico',
            tag: 'daily-health-check'
        });
    }
    
    // 화면 알림 배너
    const reminderBanner = document.createElement('div');
    reminderBanner.id = 'daily-reminder-banner';
    reminderBanner.style.cssText = `
        position: fixed;
        top: 20px;
        left: 50%;
        transform: translateX(-50%);
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 20px 30px;
        border-radius: 12px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
        z-index: 10001;
        max-width: 500px;
        text-align: center;
        animation: slideDown 0.3s ease-out;
    `;
    
    reminderBanner.innerHTML = `
        <div style="font-size: 1.2em; font-weight: 600; margin-bottom: 10px;">
            💚 오늘의 건강 체크 시간입니다!
        </div>
        <div style="margin-bottom: 15px; opacity: 0.95;">
            건강 상태를 체크하고 저장해주세요. 보호자에게도 자동으로 알림이 전송됩니다.
        </div>
        <div style="display: flex; gap: 10px; justify-content: center;">
            <button onclick="quickHealthCheck(); this.closest('div[style*=\"position: fixed\"]').remove();" 
                    style="background: white; color: #667eea; border: none; padding: 10px 20px; border-radius: 8px; font-weight: 600; cursor: pointer;">
                지금 체크하기
            </button>
            <button onclick="this.closest('div[style*=\"position: fixed\"]').remove();" 
                    style="background: rgba(255,255,255,0.2); color: white; border: 1px solid white; padding: 10px 20px; border-radius: 8px; cursor: pointer;">
                나중에
            </button>
        </div>
    `;
    
    // 스타일 추가 (한 번만)
    if (!document.getElementById('reminder-banner-style')) {
        const style = document.createElement('style');
        style.id = 'reminder-banner-style';
        style.textContent = `
            @keyframes slideDown {
                from {
                    transform: translateX(-50%) translateY(-100%);
                    opacity: 0;
                }
                to {
                    transform: translateX(-50%) translateY(0);
                    opacity: 1;
                }
            }
        `;
        document.head.appendChild(style);
    }
    
    document.body.appendChild(reminderBanner);
    
    // 30초 후 자동으로 사라지기
    setTimeout(() => {
        if (reminderBanner.parentNode) {
            reminderBanner.style.animation = 'slideDown 0.3s ease-out reverse';
            setTimeout(() => reminderBanner.remove(), 300);
        }
    }, 30000);
}

// 건강 점수 계산
function calculateHealthScore(anomalyScore, steps, sleep, hasCheckedToday) {
    let score = 100;
    
    // 이상 점수 반영 (낮을수록 좋음)
    if (anomalyScore !== null && anomalyScore !== undefined) {
        score -= Math.min(50, anomalyScore * 5); // 이상 점수 10 이상이면 50점 감점
    }
    
    // 활동량 반영
    if (steps >= 10000) {
        score += 10; // 보너스
    } else if (steps >= 5000) {
        // 정상
    } else if (steps < 1000) {
        score -= 10; // 감점
    }
    
    // 수면 시간 반영
    if (sleep >= 7 && sleep <= 9) {
        score += 5; // 보너스
    } else if (sleep < 5 || sleep > 10) {
        score -= 10; // 감점
    }
    
    // 오늘 체크 여부
    if (!hasCheckedToday) {
        score -= 5; // 체크 안 했으면 감점
    }
    
    return Math.max(0, Math.min(100, Math.round(score)));
}

// 오늘의 건강 상태 요약 업데이트
async function updateTodayHealthSummary() {
    const userId = document.getElementById('user-id').value.trim();
    if (!userId) {
        return;
    }
    
    const welcomeSection = document.getElementById('welcome-section');
    const todaySummary = document.getElementById('today-health-summary');
    const quickCheckSection = document.getElementById('quick-check-section');
    
    if (!userIdValidated) {
        todaySummary.style.display = 'none';
        quickCheckSection.style.display = 'none';
        return;
    }
    
    try {
        // 오늘 날짜
        const today = new Date().toISOString().split('T')[0];
        
        // 오늘 데이터 조회
        const response = await fetch(`/get_user/${userId}?date=${today}&limit=1`);
        const data = await response.json();
        
        const todayData = data.data && data.data.length > 0 ? data.data[0] : null;
        
        // 요약 표시
        todaySummary.style.display = 'block';
        quickCheckSection.style.display = 'block';
        
        // 오늘 체크 완료 여부
        const checkStatus = document.getElementById('today-check-status');
        if (todayData) {
            checkStatus.textContent = '완료 ✅';
            checkStatus.style.color = '#4caf50';
        } else {
            checkStatus.textContent = '미완료';
            checkStatus.style.color = '#ff9800';
        }
        
        // 건강 점수 계산
        const healthScore = document.getElementById('today-health-score');
        if (todayData) {
            const todaySteps = todayData.sensor_data && todayData.sensor_data.length > 0
                ? todayData.sensor_data.reduce((sum, sd) => sum + (sd.steps || 0), 0)
                : 0;
            const todaySleep = todayData.sensor_data && todayData.sensor_data.length > 0
                ? todayData.sensor_data.reduce((sum, sd) => sum + (sd.sleep || 0), 0) / todayData.sensor_data.length
                : 0;
            
            const score = calculateHealthScore(
                todayData.anomaly_score,
                todaySteps,
                todaySleep,
                true
            );
            
            healthScore.textContent = score + '점';
            healthScore.style.color = score >= 80 ? '#4caf50' : score >= 60 ? '#ff9800' : '#f44336';
        } else {
            healthScore.textContent = '-';
            healthScore.style.color = '#999';
        }
        
        // 긴급 연락망 개수
        const contactsCount = document.getElementById('emergency-contacts-count');
        contactsCount.textContent = emergencyContacts.length + '명';
        
    } catch (error) {
        console.error('건강 상태 요약 업데이트 실패:', error);
    }
}

// 빠른 건강 체크 (스크롤만)
function quickHealthCheck() {
    // 건강 데이터 입력 섹션으로 스크롤
    const inputSection = document.querySelector('.input-section');
    if (inputSection) {
        inputSection.scrollIntoView({ 
            behavior: 'smooth', 
            block: 'start' 
        });
        
        // 빠른 건강 체크 섹션 표시
        setTimeout(() => {
            const quickCheckSection = document.getElementById('quick-check-action-section');
            if (quickCheckSection) {
                quickCheckSection.style.display = 'block';
                quickCheckSection.scrollIntoView({ 
                    behavior: 'smooth', 
                    block: 'nearest' 
                });
            }
            
            // 스크롤 후 약간의 딜레이를 두고 섹션 강조
            inputSection.style.transition = 'box-shadow 0.3s';
            inputSection.style.boxShadow = '0 0 20px rgba(102, 126, 234, 0.3)';
            setTimeout(() => {
                inputSection.style.boxShadow = '';
            }, 2000);
        }, 500);
    }
}

// 빠른 건강 체크 실행
async function performQuickHealthCheck() {
    if (!userIdValidated) {
        showError('먼저 사용자 ID를 입력하고 확인해주세요.');
        return;
    }
    
    const userId = document.getElementById('user-id').value.trim();
    if (!userId) {
        showError('사용자 ID를 입력해주세요.');
        return;
    }
    
    // 현재 입력한 값 가져오기
    const heartRate = parseInt(document.getElementById('heart-rate')?.value) || 0;
    const steps = parseInt(document.getElementById('steps')?.value) || 0;
    const sleep = parseFloat(document.getElementById('sleep')?.value) || 0;
    const temperature = parseFloat(document.getElementById('temperature')?.value) || 0;
    
    // 입력값 검증
    if (heartRate === 0 && steps === 0 && sleep === 0 && temperature === 0) {
        showError('최소 하나 이상의 건강 데이터를 입력해주세요.');
        return;
    }
    
    // 저장 및 분석 수행
    await saveData();
    
    // 빠른 건강 체크 섹션 숨기기
    const quickCheckSection = document.getElementById('quick-check-action-section');
    if (quickCheckSection) {
        quickCheckSection.style.display = 'none';
    }
    
    // 결과 표시
    const resultDiv = document.getElementById('quick-check-result');
    if (resultDiv) {
        resultDiv.innerHTML = `
            <div style="background: #e8f5e9; padding: 15px; border-radius: 8px; border-left: 4px solid #4caf50; margin-top: 15px;">
                <strong>✅ 오늘의 건강 체크가 완료되었습니다!</strong>
                <p style="margin: 10px 0 0 0; color: #666;">건강 상태가 분석되어 저장되었고, 필요시 보호자에게도 알림이 전송되었습니다.</p>
            </div>
        `;
    }
    
    // 요약 업데이트
    setTimeout(() => {
        updateTodayHealthSummary();
    }, 1000);
}

// 응급 연락
function callEmergency() {
    const userId = document.getElementById('user-id').value.trim();
    
    if (!userId) {
        alert('먼저 사용자 ID를 입력해주세요.');
        return;
    }
    
    if (emergencyContacts.length === 0) {
        alert('긴급 연락망이 설정되지 않았습니다.\n알림 설정에서 보호자 연락처를 등록해주세요.');
        // 알림 설정 섹션으로 스크롤
        document.querySelector('.notification-section').scrollIntoView({ behavior: 'smooth' });
        return;
    }
    
    const contactList = emergencyContacts.map(c => `- ${c.name} (${c.email})`).join('\n');
    
    if (confirm(`응급 상황이신가요?\n\n긴급 연락망:\n${contactList}\n\n긴급 연락망에 알림을 전송하시겠습니까?`)) {
        // 응급 알림 API 호출
        sendEmergencyAlert(userId);
    }
}

// 긴급 알림 전송
async function sendEmergencyAlert(userId) {
    try {
        const response = await fetch('/send_emergency_alert', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                user_id: userId
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            alert('✅ 긴급 연락망에 알림이 전송되었습니다!\n\n또한 119(응급실)에 직접 연락하시는 것을 권장합니다.');
        } else {
            alert('❌ 긴급 알림 전송에 실패했습니다.\n\n' + (result.error || '알 수 없는 오류') + '\n\n이메일 설정 및 긴급 연락망을 확인해주세요.');
        }
    } catch (error) {
        console.error('긴급 알림 전송 오류:', error);
        alert('❌ 긴급 알림 전송 중 오류가 발생했습니다.\n\n서버 연결을 확인해주세요.');
    }
}

// 도움말 모달
function showHelpModal() {
    const modal = document.createElement('div');
    modal.id = 'help-modal-overlay';
    modal.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(0, 0, 0, 0.5);
        display: flex;
        justify-content: center;
        align-items: center;
        z-index: 10000;
    `;
    
    const modalContent = document.createElement('div');
    modalContent.style.cssText = `
        background: white;
        padding: 30px;
        border-radius: 16px;
        max-width: 600px;
        max-height: 80vh;
        overflow-y: auto;
        position: relative;
    `;
    
    modalContent.innerHTML = `
        <button id="close-help-modal" style="position: absolute; top: 15px; right: 15px; background: none; border: none; font-size: 28px; cursor: pointer; color: #666; width: 32px; height: 32px; display: flex; align-items: center; justify-content: center; border-radius: 50%; transition: all 0.2s;" onmouseover="this.style.background='#f0f0f0'" onmouseout="this.style.background='none'">&times;</button>
        <h2 style="margin-bottom: 20px; color: #667eea;">📖 사용 방법 안내</h2>
        <div style="line-height: 1.8; color: #333;">
            <h3 style="margin-top: 20px; margin-bottom: 10px; color: #667eea;">1. 사용자 ID 입력</h3>
            <p>처음 사용하시는 경우 원하는 ID를 입력하시면 됩니다. (영문, 숫자, _, - 만 사용 가능)</p>
            
            <h3 style="margin-top: 20px; margin-bottom: 10px; color: #667eea;">2. 건강 데이터 입력</h3>
            <p>하루에 한 번, 심박수, 걸음수, 수면 시간, 체온을 입력하세요. 정확하지 않아도 대략적인 값으로도 괜찮습니다.</p>
            
            <div style="background: #fff3cd; padding: 15px; border-radius: 8px; border-left: 4px solid #ffc107; margin: 15px 0;">
                <strong style="color: #856404;">📋 정상 범위 가이드 (정상으로 판정되기 쉬운 값):</strong>
                <ul style="margin: 10px 0 0 20px; padding: 0; color: #856404;">
                    <li><strong>심박수:</strong> 60-100 bpm (성인 기준, 안정 시) - 예: 70, 75, 80</li>
                    <li><strong>걸음수:</strong> 5000-10000 걸음/일 (일일 총 걸음수) - 예: 6000, 7000, 8000</li>
                    <li><strong>수면 시간:</strong> 6-8시간 (하루 총 수면 시간) - 예: 6.5, 7.0, 7.5</li>
                    <li><strong>체온:</strong> 36.0-37.5℃ (정상 체온) - 예: 36.3, 36.5, 36.8</li>
                </ul>
                <p style="margin: 10px 0 0 0; color: #856404; font-size: 0.9em;">
                    ⚠️ 위 범위 내의 값을 입력하시면 정상으로 판정될 가능성이 높습니다. 하지만 개인차가 있을 수 있으니 평소 자신의 정상 범위를 참고하세요.
                </p>
            </div>
            
            <h3 style="margin-top: 20px; margin-bottom: 10px; color: #667eea;">3. 건강 체크 완료</h3>
            <p>"오늘의 건강 체크 완료" 버튼을 누르시면 자동으로 분석하고 저장됩니다. 이상 징후가 감지되면 보호자에게도 알림이 전송됩니다.</p>
            
            <h3 style="margin-top: 20px; margin-bottom: 10px; color: #667eea;">4. 보호자 연락망 설정</h3>
            <p>알림 설정에서 보호자나 가족의 연락처를 등록하세요. 심각한 이상 징후가 감지되면 자동으로 연락이 갑니다.</p>
            
            <h3 style="margin-top: 20px; margin-bottom: 10px; color: #667eea;">💡 팁</h3>
            <ul style="padding-left: 20px;">
                <li>매일 같은 시간에 체크하시면 더 정확한 분석이 가능합니다.</li>
                <li>건강에 대해 궁금한 점이 있으면 챗봇에게 물어보세요.</li>
                <li>응급 상황이 발생하면 "응급 연락" 버튼을 누르세요.</li>
                <li><strong>정상으로 나오게 하려면:</strong> 위의 정상 범위 가이드를 참고하여 입력하세요. 예를 들어 심박수 70, 걸음수 6000, 수면 7시간, 체온 36.5도 같은 값이 정상 범위에 해당합니다.</li>
            </ul>
        </div>
    `;
    
    modal.appendChild(modalContent);
    document.body.appendChild(modal);
    
    // X 버튼 클릭 시 닫기
    const closeBtn = modalContent.querySelector('#close-help-modal');
    closeBtn.addEventListener('click', () => {
        modal.remove();
    });
    
    // 모달 외부 클릭 시 닫기
    modal.addEventListener('click', (e) => {
        if (e.target === modal) {
            modal.remove();
        }
    });
    
    // ESC 키로 닫기
    const handleEsc = (e) => {
        if (e.key === 'Escape') {
            modal.remove();
            document.removeEventListener('keydown', handleEsc);
        }
    };
    document.addEventListener('keydown', handleEsc);
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
    
    try {
        const response = await fetch(`/get_user/${userId}?limit=100`);
        const data = await response.json();
        
        if (data.error) {
            showError(data.error);
            return;
        }
        
        userData = data.data;
        displayUserStats(userId);
        // 차트는 history 페이지에서만 표시
        // updateTimeSeriesChart(data.data);
        
    } catch (error) {
        showError('데이터 조회 실패: ' + error.message);
    }
}

// 모든 기능 비활성화
function disableAllFeatures() {
    // 파일 업로드 버튼
    const uploadBtn = document.querySelector('.upload-controls button');
    if (uploadBtn) uploadBtn.disabled = true;
    
    // 센서 입력 필드
    const sensorInputs = document.querySelectorAll('.sensor-input-card input');
    sensorInputs.forEach(input => input.disabled = true);
    
    // 예측 및 저장 버튼
    const actionButtons = document.querySelectorAll('.sensor-action-buttons button');
    actionButtons.forEach(btn => btn.disabled = true);
    
    // 챗봇 입력
    const chatInput = document.getElementById('chat-input');
    if (chatInput) chatInput.disabled = true;
    const chatBtn = document.querySelector('.chat-input button');
    if (chatBtn) chatBtn.disabled = true;
    
    // 이메일 입력
    const emailInput = document.getElementById('notification-email');
    if (emailInput) emailInput.disabled = true;
    const emailBtn = document.getElementById('save-email-btn');
    if (emailBtn) emailBtn.disabled = true;
}

// 모든 기능 활성화
function enableAllFeatures() {
    // 파일 업로드 버튼
    const uploadBtn = document.querySelector('.upload-controls button');
    if (uploadBtn) uploadBtn.disabled = false;
    
    // 센서 입력 필드
    const sensorInputs = document.querySelectorAll('.sensor-input-card input');
    sensorInputs.forEach(input => input.disabled = false);
    
    // 예측 및 저장 버튼
    const actionButtons = document.querySelectorAll('.sensor-action-buttons button');
    actionButtons.forEach(btn => btn.disabled = false);
    
    // 챗봇 입력
    const chatInput = document.getElementById('chat-input');
    if (chatInput) chatInput.disabled = false;
    const chatBtn = document.querySelector('.chat-input button');
    if (chatBtn) chatBtn.disabled = false;
    
    // 이메일 입력
    const emailInput = document.getElementById('notification-email');
    if (emailInput) emailInput.disabled = false;
    const emailBtn = document.getElementById('save-email-btn');
    if (emailBtn) emailBtn.disabled = false;
}

// 사용자 통계 표시
async function displayUserStats(userId) {
    try {
        const response = await fetch(`/get_statistics/${userId}`);
        const stats = await response.json();
        
        const statsContainer = document.getElementById('user-stats');
        statsContainer.innerHTML = `
            <div class="stat-card">
                <h3>전체 로그 수</h3>
                <div class="value">${stats.total_logs || 0}</div>
            </div>
            <div class="stat-card">
                <h3>이상 탐지 횟수</h3>
                <div class="value">${stats.anomaly_count || 0}</div>
            </div>
            <div class="stat-card">
                <h3>이상 탐지 비율</h3>
                <div class="value">${((stats.anomaly_rate || 0) * 100).toFixed(1)}%</div>
            </div>
            <div class="stat-card">
                <h3>평균 이상 점수</h3>
                <div class="value">${(stats.avg_anomaly_score || 0).toFixed(2)}</div>
            </div>
        `;
    } catch (error) {
        console.error('통계 조회 실패:', error);
    }
}

// 이상 탐지 예측
async function predictAnomaly() {
    if (!userIdValidated) {
        showError('먼저 사용자 ID를 입력하고 확인해주세요.');
        return;
    }
    
    const userId = document.getElementById('user-id').value.trim();
    if (!userId) {
        showError('사용자 ID를 입력해주세요.');
        return;
    }
    
    // 로딩 표시
    showLoadingOverlay('이상 탐지 분석 중...');
    
    // 현재 입력한 값만 가져오기
    const heartRate = parseInt(document.getElementById('heart-rate')?.value) || 0;
    const steps = parseInt(document.getElementById('steps')?.value) || 0;
    const sleep = parseFloat(document.getElementById('sleep')?.value) || 0;
    const temperature = parseFloat(document.getElementById('temperature')?.value) || 0;
    
    // 입력값 검증
    if (heartRate === 0 && steps === 0 && sleep === 0 && temperature === 0) {
        hideLoadingOverlay();
        showError('최소 하나 이상의 건강 데이터를 입력해주세요.');
        return;
    }
    
    // activity는 걸음수 기반으로 추정 (걸음수 * 0.05로 대략 계산, 또는 기본값 300 사용)
    const activity = steps > 0 ? Math.round(steps * 0.05) : 300;
    
    // 현재 입력한 데이터만 서버로 전송 (서버에서 필요한 60개 데이터 자동 생성)
    const currentData = {
        heart_rate: heartRate,
        steps: steps,
        sleep: sleep,
        temperature: temperature,
        activity: activity  // 활동량 추가
    };
    
    try {
        const response = await fetch('/predict', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                user_id: userId,
                sensor_data: [currentData]  // 현재 입력한 값만 전송
            })
        });
        
        const result = await response.json();
        
        // 로딩 제거
        hideLoadingOverlay();
        
        if (result.error) {
            showError(result.error);
            return;
        }
        
        // 차트는 history 페이지에서만 표시
        // updateAnomalyChart(result);
        // updateTimeSeriesChart([currentData]);
        
        // 챗봇 메시지 추가
        if (result.chatbot_feedback) {
            addChatMessage('bot', result.chatbot_feedback);
            
            // 챗봇 섹션으로 스크롤
            setTimeout(() => {
                scrollToChatbot();
            }, 300);
        }
        
        // 이메일 알림 전송 결과 표시
        if (result.notification) {
            showNotificationResult(result.notification);
        }
        
    } catch (error) {
        hideLoadingOverlay();
        showError('예측 실패: ' + error.message);
    }
}

// 센서 데이터 수집 (하루에 한 번 입력)
function collectSensorData() {
    const today = new Date().toISOString().split('T')[0]; // YYYY-MM-DD 형식
    const sensorData = [{
        time: today,
        heart_rate: parseInt(document.getElementById('heart-rate')?.value) || 0,
        steps: parseInt(document.getElementById('steps')?.value) || 0,
        sleep: parseFloat(document.getElementById('sleep')?.value) || 0,
        temperature: parseFloat(document.getElementById('temperature')?.value) || 0
    }];
    
    return sensorData;
}

// 이상 탐지 결과 표시
function displayAnomalyResult(result) {
    const resultContainer = document.getElementById('anomaly-result');
    
    const isAnomaly = result.anomaly_detected;
    const anomalyClass = isAnomaly ? 'anomaly-detected' : 'anomaly-normal';
    const statusText = isAnomaly ? '⚠️ 이상 패턴 감지됨' : '✅ 정상 범위';
    
    let html = `
        <div class="${anomalyClass}">
            <h3>${statusText}</h3>
            <div class="result-item">
                <label>이상 점수:</label>
                <span class="value">${result.anomaly_score.toFixed(3)}</span>
            </div>
            <div class="result-item">
                <label>재구성 오차:</label>
                <span class="value">${result.reconstruction_error.toFixed(4)}</span>
            </div>
            <div class="result-item">
                <label>임계값:</label>
                <span class="value">${result.threshold.toFixed(4)}</span>
            </div>
    `;
    
    if (result.feature_analysis && result.feature_analysis.top_anomalous_features) {
        html += `
            <div class="result-item">
                <label>주요 이상 특징:</label>
                <span class="value">${result.feature_analysis.top_anomalous_features.map(f => translateFeatureName(f[0])).join(', ')}</span>
            </div>
        `;
    }
    
    if (result.chatbot_feedback) {
        html += `
            <div class="result-item">
                <label>챗봇 피드백:</label>
                <span class="value">${result.chatbot_feedback}</span>
            </div>
        `;
    }
    
    html += `</div>`;
    
    resultContainer.innerHTML = html;
}

// 시계열 차트 업데이트 (개선된 버전: 카드 + 원형/막대 차트)
function updateTimeSeriesChart(data) {
    const chartContainer = document.getElementById('timeseries-chart');
    if (!chartContainer) {
        console.error('timeseries-chart 요소를 찾을 수 없습니다.');
        return;
    }
    
    // 데이터 준비 (일별 데이터)
    const times = [];
    const heartRates = [];
    const steps = [];
    const temperatures = [];
    const sleeps = [];
    
    if (data && data.length > 0) {
        // 데이터 형식 확인: 로그 형식인지 직접 센서 데이터 배열인지
        const firstItem = data[0];
        
        if (firstItem.sensor_data && Array.isArray(firstItem.sensor_data)) {
            // 로그 형식: [{date: "YYYY-MM-DD", sensor_data: [...]}]
            data.forEach(log => {
                const date = log.date || new Date().toISOString().split('T')[0];
                if (log.sensor_data && Array.isArray(log.sensor_data) && log.sensor_data.length > 0) {
                    // 하루에 여러 데이터가 있으면 평균값 사용
                    const avgHeartRate = log.sensor_data.reduce((sum, sd) => sum + (sd.heart_rate || 0), 0) / log.sensor_data.length;
                    const avgSteps = log.sensor_data.reduce((sum, sd) => sum + (sd.steps || 0), 0) / log.sensor_data.length;
                    
                    times.push(date);
                    heartRates.push(Math.round(avgHeartRate));
                    steps.push(Math.round(avgSteps));
                } else {
                    // 센서 데이터가 없으면 0으로 표시
                    times.push(date);
                    heartRates.push(0);
                    steps.push(0);
                }
            });
        } else if (firstItem.time !== undefined || firstItem.heart_rate !== undefined) {
            // 직접 센서 데이터 형식: [{time: "YYYY-MM-DD", heart_rate, steps, ...}]
            // 날짜별로 그룹화하여 일별 평균 계산
            const dateMap = new Map();
            data.forEach(sd => {
                const date = sd.time || new Date().toISOString().split('T')[0];
                if (!dateMap.has(date)) {
                    dateMap.set(date, { heartRates: [], steps: [] });
                }
                const dayData = dateMap.get(date);
                dayData.heartRates.push(sd.heart_rate || 0);
                dayData.steps.push(sd.steps || 0);
            });
            
            // 날짜순 정렬
            const sortedDates = Array.from(dateMap.keys()).sort();
            sortedDates.forEach(date => {
                const dayData = dateMap.get(date);
                times.push(date);
                heartRates.push(Math.round(dayData.heartRates.reduce((a, b) => a + b, 0) / dayData.heartRates.length));
                steps.push(Math.round(dayData.steps.reduce((a, b) => a + b, 0) / dayData.steps.length));
            });
        }
    }
    
    // 데이터가 없으면 기본 차트 표시
    if (times.length === 0) {
        const today = new Date().toISOString().split('T')[0];
        times.push(today);
        heartRates.push(0);
        steps.push(0);
    }
    
    try {
        // 최근 데이터 계산
        const latestHeartRate = heartRates.length > 0 ? heartRates[heartRates.length - 1] : 0;
        const latestSteps = steps.length > 0 ? steps[steps.length - 1] : 0;
        const avgHeartRate = heartRates.length > 0 ? Math.round(heartRates.reduce((a, b) => a + b, 0) / heartRates.length) : 0;
        const avgSteps = steps.length > 0 ? Math.round(steps.reduce((a, b) => a + b, 0) / steps.length) : 0;
        const totalSteps = steps.reduce((a, b) => a + b, 0);
        
        // 날짜 포맷팅
        const formattedTimes = times.map(date => {
            if (date && date.includes('-')) {
                const parts = date.split('-');
                return `${parts[1]}/${parts[2]}`;
            }
            return date;
        });
        
        // 막대 그래프로 변경 (더 직관적)
        const trace1 = {
            x: formattedTimes,
            y: heartRates,
            type: 'bar',
            name: '심박수',
            marker: {
                color: heartRates.map(hr => {
                    if (hr >= 100) return '#ff4757'; // 높음
                    if (hr >= 60 && hr < 100) return '#2ed573'; // 정상
                    return '#ffa502'; // 낮음
                }),
                line: { width: 1, color: '#fff' }
            },
            hovertemplate: '<b>심박수</b><br>날짜: %{x}<br>심박수: %{y} bpm<extra></extra>',
            text: heartRates.map(v => v + ' bpm'),
            textposition: 'outside',
            textfont: { size: 10, color: '#333' }
        };
        
        const trace2 = {
            x: formattedTimes,
            y: steps,
            type: 'bar',
            name: '걸음수',
            yaxis: 'y2',
            marker: {
                color: '#4ecdc4',
                line: { width: 1, color: '#fff' }
            },
            hovertemplate: '<b>걸음수</b><br>날짜: %{x}<br>걸음수: %{y.toLocaleString()} 걸음<extra></extra>',
            text: steps.map(v => v > 0 ? (v.toLocaleString() + ' 걸음') : ''),
            textposition: 'outside',
            textfont: { size: 10, color: '#333' }
        };
        
        // 원형 차트 데이터 (건강 지표 분포)
        const pieData = [
            { label: '정상 심박수', value: heartRates.filter(hr => hr >= 60 && hr < 100).length, color: '#2ed573' },
            { label: '높은 심박수', value: heartRates.filter(hr => hr >= 100).length, color: '#ff4757' },
            { label: '낮은 심박수', value: heartRates.filter(hr => hr < 60).length, color: '#ffa502' }
        ].filter(item => item.value > 0);
        
        const pieTrace = {
            labels: pieData.map(d => d.label),
            values: pieData.map(d => d.value),
            type: 'pie',
            hole: 0.5,
            marker: {
                colors: pieData.map(d => d.color),
                line: { width: 2, color: '#fff' }
            },
            textinfo: 'label+percent',
            textposition: 'outside',
            hovertemplate: '<b>%{label}</b><br>일수: %{value}일<br>비율: %{percent}<extra></extra>'
        };
        
        const layout = {
            title: {
                text: '일별 건강 데이터',
                font: { 
                    size: 18, 
                    color: '#1a1a1a',
                    family: 'Malgun Gothic, 맑은 고딕, Arial, sans-serif',
                    weight: 'bold'
                },
                x: 0.5,
                xanchor: 'center',
                pad: { t: 10 }
            },
            xaxis: { 
                title: { 
                    text: '날짜', 
                    font: { size: 14, color: '#333', family: 'Malgun Gothic, 맑은 고딕' } 
                },
                showgrid: true,
                gridcolor: 'rgba(0, 0, 0, 0.1)',
                gridwidth: 1,
                tickangle: -30,
                tickfont: { size: 11, color: '#666' },
                type: 'category'
            },
            yaxis: { 
                title: { 
                    text: '심박수 (bpm)', 
                    font: { size: 14, color: '#ff6b6b', family: 'Malgun Gothic, 맑은 고딕', weight: 'bold' } 
                },
                side: 'left',
                showgrid: true,
                gridcolor: 'rgba(255, 107, 107, 0.15)',
                gridwidth: 1,
                zeroline: true,
                zerolinecolor: 'rgba(0, 0, 0, 0.2)',
                tickfont: { size: 11, color: '#ff6b6b' }
            },
            yaxis2: { 
                title: { 
                    text: '걸음수', 
                    font: { size: 14, color: '#4ecdc4', family: 'Malgun Gothic, 맑은 고딕', weight: 'bold' } 
                },
                overlaying: 'y', 
                side: 'right',
                showgrid: false,
                zeroline: false,
                tickfont: { size: 11, color: '#4ecdc4' }
            },
            hovermode: 'x unified',
            showlegend: true,
            legend: {
                x: 1.02,
                y: 1,
                xanchor: 'left',
                yanchor: 'top',
                bgcolor: 'rgba(255, 255, 255, 0.95)',
                bordercolor: '#ccc',
                borderwidth: 1,
                font: { size: 13, color: '#333', family: 'Malgun Gothic, 맑은 고딕' }
            },
            plot_bgcolor: '#ffffff',
            paper_bgcolor: 'rgba(255, 255, 255, 0)',
            autosize: true,
            margin: { l: 70, r: 80, t: 60, b: 70 },
            height: 450,
            barmode: 'group'
        };
        
        const pieLayout = {
            title: {
                text: '심박수 분포',
                font: { size: 16, color: '#333', family: 'Malgun Gothic, 맑은 고딕' },
                x: 0.5,
                xanchor: 'center'
            },
            showlegend: true,
            legend: {
                x: 0.5,
                y: -0.1,
                xanchor: 'center',
                orientation: 'h',
                font: { size: 12, family: 'Malgun Gothic, 맑은 고딕' }
            },
            paper_bgcolor: 'rgba(255, 255, 255, 0)',
            plot_bgcolor: '#ffffff',
            height: 300
        };
        
        // 카드 형태의 요약 정보 HTML 생성
        const summaryHTML = `
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-bottom: 20px;">
                <div style="background: linear-gradient(135deg, #ff6b6b 0%, #ee5a6f 100%); padding: 20px; border-radius: 12px; color: white; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                    <div style="font-size: 14px; opacity: 0.9; margin-bottom: 8px;">현재 심박수</div>
                    <div style="font-size: 32px; font-weight: bold;">${latestHeartRate}</div>
                    <div style="font-size: 12px; opacity: 0.8;">bpm</div>
                </div>
                <div style="background: linear-gradient(135deg, #4ecdc4 0%, #44a08d 100%); padding: 20px; border-radius: 12px; color: white; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                    <div style="font-size: 14px; opacity: 0.9; margin-bottom: 8px;">현재 걸음수</div>
                    <div style="font-size: 32px; font-weight: bold;">${latestSteps.toLocaleString()}</div>
                    <div style="font-size: 12px; opacity: 0.8;">걸음</div>
                </div>
                <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 20px; border-radius: 12px; color: white; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                    <div style="font-size: 14px; opacity: 0.9; margin-bottom: 8px;">평균 심박수</div>
                    <div style="font-size: 32px; font-weight: bold;">${avgHeartRate}</div>
                    <div style="font-size: 12px; opacity: 0.8;">bpm</div>
                </div>
                <div style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); padding: 20px; border-radius: 12px; color: white; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                    <div style="font-size: 14px; opacity: 0.9; margin-bottom: 8px;">총 걸음수</div>
                    <div style="font-size: 32px; font-weight: bold;">${totalSteps.toLocaleString()}</div>
                    <div style="font-size: 12px; opacity: 0.8;">걸음</div>
                </div>
            </div>
            <div style="display: grid; grid-template-columns: 2fr 1fr; gap: 20px; margin-top: 20px;">
                <div id="bar-chart-container" style="background: white; padding: 20px; border-radius: 12px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);"></div>
                <div id="pie-chart-container" style="background: white; padding: 20px; border-radius: 12px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);"></div>
            </div>
        `;
        
        chartContainer.innerHTML = summaryHTML;
        
        const config = {
            responsive: true,
            displayModeBar: true,
            displaylogo: false,
            modeBarButtonsToRemove: ['pan2d', 'lasso2d', 'select2d'],
            autosizable: true
        };
        
        // 막대 그래프 생성
        Plotly.newPlot('bar-chart-container', [trace1, trace2], layout, config);
        
        // 원형 차트 생성
        if (pieData.length > 0) {
            Plotly.newPlot('pie-chart-container', [pieTrace], pieLayout, config);
        } else {
            document.getElementById('pie-chart-container').innerHTML = '<div style="text-align: center; padding: 40px; color: #999;">데이터가 없습니다.</div>';
        }
        
    } catch (error) {
        console.error('시계열 차트 생성 실패:', error);
        chartContainer.innerHTML = '<div class="chart-error">차트를 표시할 수 없습니다.<br>오류: ' + error.message + '</div>';
    }
}

// 이상 탐지 차트 업데이트
function updateAnomalyChart(result) {
    const chartContainer = document.getElementById('anomaly-chart');
    if (!chartContainer) {
        console.error('anomaly-chart 요소를 찾을 수 없습니다.');
        return;
    }
    
    if (!result) {
        console.error('차트 데이터가 없습니다.');
        return;
    }
    
    const times = [];
    const anomalyScores = [];
    const threshold = result.threshold || 0.01;
    
    // 최근 데이터로 차트 업데이트 (일별 데이터)
    if (userData && userData.length > 0) {
        userData.forEach(log => {
            if (log.anomaly_score !== null && log.anomaly_score !== undefined) {
                const dateStr = log.date || new Date().toISOString().split('T')[0];
                times.push(dateStr);
                anomalyScores.push(parseFloat(log.anomaly_score) || 0);
            }
        });
    }
    
    // 현재 결과 추가 (오늘 날짜)
    const today = new Date().toISOString().split('T')[0];
    // 이미 오늘 날짜가 있으면 업데이트, 없으면 추가
    const todayIndex = times.indexOf(today);
    if (todayIndex >= 0) {
        anomalyScores[todayIndex] = parseFloat(result.anomaly_score) || 0;
    } else {
        times.push(today);
        anomalyScores.push(parseFloat(result.anomaly_score) || 0);
    }
    
    // 날짜순 정렬
    const sortedData = times.map((time, i) => ({ time, score: anomalyScores[i] }))
        .sort((a, b) => new Date(a.time) - new Date(b.time));
    times.length = 0;
    anomalyScores.length = 0;
    sortedData.forEach(item => {
        times.push(item.time);
        anomalyScores.push(item.score);
    });
    
    // 데이터가 없으면 기본 값 추가
    if (times.length === 0) {
        times.push(today);
        anomalyScores.push(0);
    }
    
    try {
        // 현재 이상 점수
        const currentScore = anomalyScores.length > 0 ? anomalyScores[anomalyScores.length - 1] : 0;
        const maxScore = Math.max(...anomalyScores, threshold, 1);
        
        // 이상 여부에 따른 상태
        const getStatus = (score) => {
            if (score > threshold) return { text: '이상', color: '#ff4757', bg: '#fff5f5' };
            if (score > threshold * 0.7) return { text: '주의', color: '#ffa502', bg: '#fffbf0' };
            return { text: '정상', color: '#2ed573', bg: '#f0fff4' };
        };
        
        const currentStatus = getStatus(currentScore);
        
        // 날짜 포맷팅
        const formattedTimes = times.map(date => {
            if (date && date.includes('-')) {
                const parts = date.split('-');
                return `${parts[1]}/${parts[2]}`;
            }
            return date;
        });
        
        // 게이지 차트 (현재 이상 점수)
        const gaugeValue = Math.min(100, (currentScore / Math.max(threshold * 2, 1)) * 100);
        const gaugeData = [{
            domain: { x: [0, 1], y: [0, 1] },
            value: gaugeValue,
            title: { text: "현재 이상 점수", font: { size: 16, family: 'Malgun Gothic, 맑은 고딕' } },
            type: "indicator",
            mode: "gauge+number",
            gauge: {
                axis: { range: [null, 100], tickwidth: 1, tickcolor: "#333" },
                bar: { color: currentStatus.color },
                bgcolor: "white",
                borderwidth: 2,
                bordercolor: currentStatus.color,
                steps: [
                    { range: [0, 50], color: "#2ed573" },
                    { range: [50, 80], color: "#ffa502" },
                    { range: [80, 100], color: "#ff4757" }
                ],
                threshold: {
                    line: { color: "#ff4757", width: 4 },
                    thickness: 0.75,
                    value: (threshold / Math.max(threshold * 2, 1)) * 100
                }
            }
        }];
        
        const gaugeLayout = {
            paper_bgcolor: "white",
            font: { color: "#333", family: 'Malgun Gothic, 맑은 고딕' },
            height: 300,
            margin: { t: 0, b: 0, l: 0, r: 0 }
        };
        
        // 막대 그래프 (일별 이상 점수)
        const barTrace = {
            x: formattedTimes,
            y: anomalyScores,
            type: 'bar',
            name: '이상 점수',
            marker: {
                color: anomalyScores.map(score => {
                    if (score > threshold) return '#ff4757';
                    if (score > threshold * 0.7) return '#ffa502';
                    return '#2ed573';
                }),
                line: { width: 1, color: '#fff' }
            },
            hovertemplate: '<b>이상 점수</b><br>날짜: %{x}<br>점수: %{y:.3f}<extra></extra>',
            text: anomalyScores.map(v => v.toFixed(2)),
            textposition: 'outside',
            textfont: { size: 10, color: '#333' }
        };
        
        const barLayout = {
            title: {
                text: '일별 이상 탐지 점수',
                font: { size: 16, color: '#333', family: 'Malgun Gothic, 맑은 고딕' },
                x: 0.5,
                xanchor: 'center'
            },
            xaxis: { 
                title: { text: '날짜', font: { size: 12, family: 'Malgun Gothic, 맑은 고딕' } },
                showgrid: true,
                gridcolor: 'rgba(0, 0, 0, 0.1)',
                tickangle: -30,
                tickfont: { size: 10 }
            },
            yaxis: { 
                title: { text: '이상 점수', font: { size: 12, family: 'Malgun Gothic, 맑은 고딕' } },
                showgrid: true,
                gridcolor: 'rgba(0, 0, 0, 0.1)',
                zeroline: true
            },
            shapes: [{
                type: 'line',
                xref: 'paper',
                yref: 'y',
                x0: 0,
                y0: threshold,
                x1: 1,
                y1: threshold,
                line: { color: '#ff4757', width: 2, dash: 'dash' }
            }],
            annotations: [{
                xref: 'paper',
                yref: 'y',
                x: 0.98,
                y: threshold,
                text: `임계값: ${threshold.toFixed(3)}`,
                showarrow: true,
                arrowhead: 2,
                arrowcolor: '#ff4757',
                bgcolor: 'rgba(255, 255, 255, 0.9)',
                bordercolor: '#ff4757',
                borderwidth: 1,
                font: { size: 10, color: '#ff4757', family: 'Malgun Gothic, 맑은 고딕' }
            }],
            paper_bgcolor: 'white',
            plot_bgcolor: '#ffffff',
            height: 300,
            margin: { t: 50, b: 60, l: 60, r: 40 }
        };
        
        // 요약 카드 HTML
        const summaryHTML = `
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-bottom: 20px;">
                <div style="background: linear-gradient(135deg, ${currentStatus.color} 0%, ${currentStatus.color}dd 100%); padding: 20px; border-radius: 12px; color: white; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                    <div style="font-size: 14px; opacity: 0.9; margin-bottom: 8px;">현재 상태</div>
                    <div style="font-size: 32px; font-weight: bold;">${currentStatus.text}</div>
                    <div style="font-size: 12px; opacity: 0.8;">이상 점수: ${currentScore.toFixed(3)}</div>
                </div>
                <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 20px; border-radius: 12px; color: white; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                    <div style="font-size: 14px; opacity: 0.9; margin-bottom: 8px;">임계값</div>
                    <div style="font-size: 32px; font-weight: bold;">${threshold.toFixed(3)}</div>
                    <div style="font-size: 12px; opacity: 0.8;">기준선</div>
                </div>
                <div style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); padding: 20px; border-radius: 12px; color: white; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                    <div style="font-size: 14px; opacity: 0.9; margin-bottom: 8px;">이상 감지 일수</div>
                    <div style="font-size: 32px; font-weight: bold;">${anomalyScores.filter(s => s > threshold).length}</div>
                    <div style="font-size: 12px; opacity: 0.8;">/${anomalyScores.length}일</div>
                </div>
            </div>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-top: 20px;">
                <div id="gauge-chart-container" style="background: white; padding: 20px; border-radius: 12px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);"></div>
                <div id="bar-chart-container" style="background: white; padding: 20px; border-radius: 12px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);"></div>
            </div>
        `;
        
        chartContainer.innerHTML = summaryHTML;
        
        const config = {
            responsive: true,
            displayModeBar: true,
            displaylogo: false,
            modeBarButtonsToRemove: ['pan2d', 'lasso2d', 'select2d'],
            autosizable: true
        };
        
        // 게이지 차트 생성
        Plotly.newPlot('gauge-chart-container', gaugeData, gaugeLayout, config);
        
        // 막대 그래프 생성
        Plotly.newPlot('bar-chart-container', [barTrace], barLayout, config);
        
    } catch (error) {
        console.error('이상 탐지 차트 생성 실패:', error);
        chartContainer.innerHTML = '<div class="chart-error">차트를 표시할 수 없습니다.<br>오류: ' + error.message + '</div>';
    }
}

// 데이터 저장
async function saveData() {
    if (!userIdValidated) {
        showError('먼저 사용자 ID를 입력하고 확인해주세요.');
        return;
    }
    
    const userId = document.getElementById('user-id').value.trim();
    if (!userId) {
        showError('사용자 ID를 입력해주세요.');
        return;
    }
    
    // 현재 입력한 값 가져오기
    const heartRate = parseInt(document.getElementById('heart-rate')?.value) || 0;
    const steps = parseInt(document.getElementById('steps')?.value) || 0;
    const sleep = parseFloat(document.getElementById('sleep')?.value) || 0;
    const temperature = parseFloat(document.getElementById('temperature')?.value) || 0;
    
    // 입력값 검증
    if (heartRate === 0 && steps === 0 && sleep === 0 && temperature === 0) {
        showError('최소 하나 이상의 건강 데이터를 입력해주세요.');
        return;
    }
    
    // activity는 걸음수 기반으로 추정 (걸음수 * 0.05로 대략 계산, 또는 기본값 300 사용)
    // 정상 범위: 200-500 정도 (활동량 칼로리 기준)
    const activity = steps > 0 ? Math.round(steps * 0.05) : 300;
    
    const currentData = {
        heart_rate: heartRate,
        steps: steps,
        sleep: sleep,
        temperature: temperature,
        activity: activity  // 활동량 추가 (걸음수 기반 추정 또는 기본값)
    };
    
    const sensorData = [currentData];
    
    // 로딩 표시
    showLoadingOverlay('데이터 저장 및 분석 중...');
    
    try {
        // 먼저 이상 탐지 수행
        const predictResponse = await fetch('/predict', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                user_id: userId,
                sensor_data: sensorData
            })
        });
        
        const predictResult = await predictResponse.json();
        
        if (predictResult.error) {
            hideLoadingOverlay();
            showError('이상 탐지 실패: ' + predictResult.error);
            return;
        }
        
        // 이상 탐지 결과를 포함하여 저장
        const saveResponse = await fetch('/save_data', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                user_id: userId,
                date: new Date().toISOString().split('T')[0],
                sensor_data: sensorData,
                anomaly_score: predictResult.anomaly_score,
                anomaly_detected: predictResult.anomaly_detected,
                chatbot_feedback: predictResult.chatbot_feedback
            })
        });
        
        const saveResult = await saveResponse.json();
        
        hideLoadingOverlay();
        
        if (saveResult.error) {
            showError(saveResult.error);
            return;
        }
        
        // 챗봇 피드백 표시
        if (predictResult.chatbot_feedback) {
            addChatMessage('bot', predictResult.chatbot_feedback);
        }
        
        // 이메일 알림 전송 결과 표시
        if (predictResult.notification) {
            showNotificationResult(predictResult.notification);
        }
        
        // 요약 업데이트
        updateTodayHealthSummary();
        updateGoalProgress(); // 목표 진행률 업데이트
        
        alert('✅ 오늘의 건강 체크가 완료되었습니다!\n\n건강 상태가 분석되어 저장되었고, 필요시 보호자에게도 알림이 전송되었습니다.');
        loadUserData(); // 데이터 새로고침
        
    } catch (error) {
        hideLoadingOverlay();
        showError('저장 실패: ' + error.message);
    }
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
        const response = await fetch('/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                message: message,
                user_id: currentUserId
            })
        });
        
        const data = await response.json();
        
        if (data.error) {
            addChatMessage('bot', '죄송합니다. 오류가 발생했습니다: ' + data.error);
            return;
        }
        
        // 챗봇 응답 표시
        addChatMessage('bot', data.response);
        
        // 현재 알림이 있으면 응답했다고 표시
        if (currentNotificationId) {
            markNotificationResponded(currentNotificationId);
            currentNotificationId = null;
        }
        
    } catch (error) {
        addChatMessage('bot', '죄송합니다. 연결 오류가 발생했습니다.');
    }
}

// 챗봇 메시지 추가
function addChatMessage(type, message) {
    const messagesContainer = document.getElementById('chat-messages');
    const messageDiv = document.createElement('div');
    messageDiv.className = `chat-message ${type}`;
    messageDiv.textContent = message;
    messagesContainer.appendChild(messageDiv);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

// 엔터키 처리
function handleChatKeyPress(event) {
    if (event.key === 'Enter') {
        sendChatMessage();
    }
}

// 로딩 표시
function showLoading(elementId, message) {
    const element = document.getElementById(elementId);
    element.innerHTML = `
        <div class="loading">
            <div class="spinner"></div>
            <p>${message}</p>
        </div>
    `;
}

// 에러 표시
function showError(message) {
    alert(message);
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
    
    if (!userId) {
        showError('사용자 ID를 입력해주세요.');
        return;
    }
    const statusDiv = document.getElementById('upload-status');
    const fileLabel = document.querySelector('.file-text');
    
    if (!file) {
        statusDiv.innerHTML = '<p style="color: #ef4444; padding: 10px; background: #fee; border-radius: 8px;">파일을 선택해주세요.</p>';
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
                <button onclick="loadUserData()" class="btn-secondary" style="margin-top: 15px;">데이터 새로고침</button>
            </div>
        `;
        
        // 챗봇 피드백 추가
        console.log('업로드 결과:', result);
        if (result.chatbot_feedback) {
            console.log('챗봇 피드백:', result.chatbot_feedback);
            addChatMessage('bot', result.chatbot_feedback);
            
            // 챗봇 섹션으로 스크롤
            setTimeout(() => {
                scrollToChatbot();
            }, 300);
        } else {
            console.warn('챗봇 피드백이 없습니다. 서버 응답:', result);
            // 피드백이 없어도 기본 메시지 추가
            const defaultMessage = result.anomaly_detected 
                ? '⚠️ 건강 데이터에서 이상 패턴이 감지되었습니다. 건강 상태를 확인해보시기 바랍니다.'
                : '✅ 건강 데이터가 정상 범위 내에 있습니다. 계속해서 건강을 관리해주세요.';
            addChatMessage('bot', defaultMessage);
            setTimeout(() => {
                scrollToChatbot();
            }, 300);
        }
        
        // 차트는 history 페이지에서만 표시
        // if (result.anomaly_score !== undefined) {
        //     updateAnomalyChart(result);
        // }
        
        // 데이터 새로고침
        loadUserData();
        
    } catch (error) {
            statusDiv.innerHTML = `<div style="padding: 15px; background: #fee; border-radius: 8px; border-left: 4px solid #ef4444;"><p style="color: #dc2626; font-weight: 600;">❌ 업로드 실패: ${error.message}</p></div>`;
    }
}

// 알림 설정 관련 함수
async function saveNotificationEmail() {
    if (!userIdValidated) {
        showError('먼저 사용자 ID를 입력하고 확인해주세요.');
        return;
    }
    
    const userId = document.getElementById('user-id').value.trim();
    if (!userId) {
        showError('사용자 ID를 입력해주세요.');
        return;
    }
    const email = document.getElementById('notification-email').value.trim();
    const statusDiv = document.getElementById('notification-save-status');
    const emailInput = document.getElementById('notification-email');
    const saveBtn = document.getElementById('save-email-btn');
    const editBtn = document.getElementById('edit-email-btn');
    
    if (!email) {
        statusDiv.textContent = '❌ 이메일 주소를 입력하세요.';
        statusDiv.style.color = '#dc3545';
        setTimeout(() => {
            statusDiv.textContent = '';
        }, 3000);
        return;
    }
    
    try {
        // config.py의 user_emails에 저장하기 위해 서버 API 호출
        // 간단하게 config.py를 직접 수정하는 대신, 서버에서 처리하도록
        const response = await fetch('/update_user_email', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                user_id: userId,
                email: email
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            statusDiv.textContent = '✅ 이메일 주소가 저장되었습니다!';
            statusDiv.style.color = '#28a745';
            
            // 저장 성공 시 입력 필드 비활성화 및 버튼 전환
            emailInput.disabled = true;
            saveBtn.style.display = 'none';
            editBtn.style.display = 'inline-block';
        } else {
            statusDiv.textContent = '❌ 저장 실패: ' + (result.error || '알 수 없는 오류');
            statusDiv.style.color = '#dc3545';
        }
        
        setTimeout(() => {
            statusDiv.textContent = '';
        }, 3000);
    } catch (error) {
        statusDiv.textContent = '❌ 저장 실패: 서버 연결 오류';
        statusDiv.style.color = '#dc3545';
        console.error('이메일 저장 실패:', error);
        setTimeout(() => {
            statusDiv.textContent = '';
        }, 3000);
    }
}

// 이메일 편집 모드로 전환
function editNotificationEmail() {
    const emailInput = document.getElementById('notification-email');
    const saveBtn = document.getElementById('save-email-btn');
    const editBtn = document.getElementById('edit-email-btn');
    
    emailInput.disabled = false;
    emailInput.focus();
    saveBtn.style.display = 'inline-block';
    editBtn.style.display = 'none';
}

// 페이지 로드 시 이메일 주소 불러오기 (서버에서 가져오기)
async function loadNotificationEmail() {
    if (!userIdValidated) {
        return;
    }
    
    const userId = document.getElementById('user-id').value.trim();
    if (!userId) {
        return;
    }
    const emailInput = document.getElementById('notification-email');
    const saveBtn = document.getElementById('save-email-btn');
    const editBtn = document.getElementById('edit-email-btn');
    
    try {
        const response = await fetch(`/get_user_email/${userId}`);
        const result = await response.json();
        
        if (result.success && result.email) {
            // 서버에 저장된 이메일이 있으면 표시하고 비활성화
            emailInput.value = result.email;
            emailInput.disabled = true;
            saveBtn.style.display = 'none';
            editBtn.style.display = 'inline-block';
        } else {
            // 저장된 이메일이 없으면 빈 상태로 활성화
            emailInput.value = '';
            emailInput.disabled = false;
            saveBtn.style.display = 'inline-block';
            editBtn.style.display = 'none';
        }
    } catch (error) {
        // 서버 오류 시 빈 상태로 시작
        console.error('이메일 로드 실패:', error);
        emailInput.value = '';
        emailInput.disabled = false;
        saveBtn.style.display = 'inline-block';
        editBtn.style.display = 'none';
    }
}

// 이메일 알림 전송 결과 표시
function showNotificationResult(notification) {
    if (!notification) {
        return;
    }
    
    let message = '';
    let type = 'info'; // 'success', 'error', 'info'
    
    if (notification.sent) {
        if (notification.email_sent) {
            message = '✅ 이메일 알림이 성공적으로 전송되었습니다.';
            type = 'success';
        }
        
        if (notification.emergency_sent) {
            if (message) {
                message += '\n🚨 긴급 연락망에도 알림이 전송되었습니다.';
            } else {
                message = '🚨 긴급 연락망에 알림이 전송되었습니다.';
            }
            type = 'success';
        }
        
        if (notification.alert_level) {
            const levelNames = {
                'low': '낮음',
                'medium': '중간',
                'high': '높음',
                'critical': '심각'
            };
            message += `\n알림 레벨: ${levelNames[notification.alert_level] || notification.alert_level}`;
        }
    } else {
        if (notification.reason) {
            if (notification.reason === '정상 범위') {
                // 정상 범위면 알림 표시 안 함
                return;
            }
            message = `ℹ️ 알림 미전송: ${notification.reason}`;
        } else if (notification.error) {
            message = `❌ 이메일 전송 실패: ${notification.error}`;
            type = 'error';
        } else {
            message = 'ℹ️ 알림이 전송되지 않았습니다.';
        }
    }
    
    if (message) {
        // 알림 배너 표시
        showNotificationBanner(message, type);
    }
}

// 알림 배너 표시
function showNotificationBanner(message, type = 'info') {
    // 기존 배너 제거
    const existingBanner = document.getElementById('email-notification-banner');
    if (existingBanner) {
        existingBanner.remove();
    }
    
    // 배너 생성
    const banner = document.createElement('div');
    banner.id = 'email-notification-banner';
    banner.className = `email-notification-banner ${type}`;
    banner.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: ${type === 'success' ? '#28a745' : type === 'error' ? '#dc3545' : '#17a2b8'};
        color: white;
        padding: 15px 20px;
        border-radius: 8px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        z-index: 10000;
        max-width: 400px;
        animation: slideIn 0.3s ease-out;
    `;
    
    // 스타일 추가 (한 번만)
    if (!document.getElementById('email-notification-style')) {
        const style = document.createElement('style');
        style.id = 'email-notification-style';
        style.textContent = `
            @keyframes slideIn {
                from {
                    transform: translateX(100%);
                    opacity: 0;
                }
                to {
                    transform: translateX(0);
                    opacity: 1;
                }
            }
            @keyframes slideOut {
                from {
                    transform: translateX(0);
                    opacity: 1;
                }
                to {
                    transform: translateX(100%);
                    opacity: 0;
                }
            }
            .email-notification-banner {
                font-family: 'Noto Sans KR', sans-serif;
                font-size: 14px;
                line-height: 1.5;
                white-space: pre-line;
            }
            .email-notification-banner .close-btn {
                position: absolute;
                top: 5px;
                right: 10px;
                background: none;
                border: none;
                color: white;
                font-size: 20px;
                cursor: pointer;
                padding: 0;
                width: 24px;
                height: 24px;
                display: flex;
                align-items: center;
                justify-content: center;
            }
            .email-notification-banner .close-btn:hover {
                opacity: 0.8;
            }
        `;
        document.head.appendChild(style);
    }
    
    // 닫기 버튼 추가
    const closeBtn = document.createElement('button');
    closeBtn.className = 'close-btn';
    closeBtn.innerHTML = '&times;';
    closeBtn.onclick = () => {
        banner.style.animation = 'slideOut 0.3s ease-out';
        setTimeout(() => banner.remove(), 300);
    };
    
    banner.innerHTML = message.replace(/\n/g, '<br>');
    banner.appendChild(closeBtn);
    
    document.body.appendChild(banner);
    
    // 5초 후 자동으로 사라지기
    setTimeout(() => {
        if (banner.parentNode) {
            banner.style.animation = 'slideOut 0.3s ease-out';
            setTimeout(() => banner.remove(), 300);
        }
    }, 5000);
}

// 긴급 연락망 목록 (메모리에 저장)
let emergencyContacts = [];

// 긴급 연락망 추가
function addEmergencyContact() {
    const name = document.getElementById('emergency-name').value.trim();
    const email = document.getElementById('emergency-email').value.trim();
    const phone = document.getElementById('emergency-phone').value.trim();
    
    if (!name || !email) {
        alert('이름과 이메일은 필수 입력 항목입니다.');
        return;
    }
    
    // 이메일 형식 검증
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
        alert('올바른 이메일 형식을 입력해주세요.');
        return;
    }
    
    // 중복 체크
    if (emergencyContacts.some(contact => contact.email === email)) {
        alert('이미 등록된 이메일 주소입니다.');
        return;
    }
    
    const contact = {
        name: name,
        email: email,
        phone: phone || ''
    };
    
    emergencyContacts.push(contact);
    renderEmergencyContacts();
    
    // 입력 필드 초기화
    document.getElementById('emergency-name').value = '';
    document.getElementById('emergency-email').value = '';
    document.getElementById('emergency-phone').value = '';
}

// 긴급 연락망 삭제
function removeEmergencyContact(index) {
    if (confirm('이 연락처를 삭제하시겠습니까?')) {
        emergencyContacts.splice(index, 1);
        renderEmergencyContacts();
    }
}

// 긴급 연락망 목록 렌더링
function renderEmergencyContacts() {
    const listDiv = document.getElementById('emergency-contacts-list');
    
    if (emergencyContacts.length === 0) {
        listDiv.innerHTML = '<p style="color: #666; padding: 20px; text-align: center; background: #f8f9fa; border-radius: 8px;">등록된 긴급 연락망이 없습니다.</p>';
        return;
    }
    
    let html = '<div class="emergency-contacts-grid" style="display: grid; gap: 15px;">';
    emergencyContacts.forEach((contact, index) => {
        html += `
            <div class="emergency-contact-item" style="padding: 15px; background: white; border: 1px solid #e0e0e0; border-radius: 8px; display: flex; justify-content: space-between; align-items: center;">
                <div style="flex: 1;">
                    <div style="font-weight: 600; margin-bottom: 5px;">${escapeHtml(contact.name)}</div>
                    <div style="color: #666; font-size: 14px; margin-bottom: 3px;">📧 ${escapeHtml(contact.email)}</div>
                    ${contact.phone ? `<div style="color: #666; font-size: 14px;">📞 ${escapeHtml(contact.phone)}</div>` : ''}
                </div>
                <button onclick="removeEmergencyContact(${index})" class="btn-secondary btn-small" style="margin-left: 15px;">삭제</button>
            </div>
        `;
    });
    html += '</div>';
    listDiv.innerHTML = html;
}

// 긴급 연락망 저장
async function saveEmergencyContacts() {
    const userId = document.getElementById('user-id').value.trim();
    if (!userId) {
        alert('사용자 ID를 먼저 입력해주세요.');
        return;
    }
    
    const statusDiv = document.getElementById('emergency-save-status');
    
    try {
        const response = await fetch('/update_emergency_contacts', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                user_id: userId,
                contacts: emergencyContacts
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            statusDiv.textContent = '✅ 긴급 연락망이 저장되었습니다!';
            statusDiv.style.color = '#28a745';
        } else {
            statusDiv.textContent = '❌ 저장 실패: ' + (result.error || '알 수 없는 오류');
            statusDiv.style.color = '#dc3545';
        }
        
        setTimeout(() => {
            statusDiv.textContent = '';
        }, 3000);
    } catch (error) {
        statusDiv.textContent = '❌ 저장 실패: 서버 연결 오류';
        statusDiv.style.color = '#dc3545';
        console.error('긴급 연락망 저장 실패:', error);
        setTimeout(() => {
            statusDiv.textContent = '';
        }, 3000);
    }
}

// 긴급 연락망 불러오기
async function loadEmergencyContacts() {
    const userId = document.getElementById('user-id').value.trim();
    if (!userId) {
        return;
    }
    
    try {
        const response = await fetch(`/get_emergency_contacts/${userId}`);
        const result = await response.json();
        
        if (result.success && result.contacts && result.contacts.length > 0) {
        emergencyContacts = result.contacts;
        renderEmergencyContacts();
        updateTodayHealthSummary(); // 요약 업데이트
        } else {
            emergencyContacts = [];
            renderEmergencyContacts();
        }
    } catch (error) {
        console.error('긴급 연락망 로드 실패:', error);
        emergencyContacts = [];
        renderEmergencyContacts();
    }
}

// HTML 이스케이프 함수
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// 로딩 오버레이 표시
function showLoadingOverlay(message) {
    // 기존 오버레이가 있으면 제거
    let overlay = document.getElementById('loading-overlay');
    if (overlay) {
        overlay.remove();
    }
    
    // 새 오버레이 생성
    overlay = document.createElement('div');
    overlay.id = 'loading-overlay';
    overlay.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(0, 0, 0, 0.7);
        display: flex;
        justify-content: center;
        align-items: center;
        z-index: 10000;
        backdrop-filter: blur(5px);
    `;
    
    const content = document.createElement('div');
    content.style.cssText = `
        background: white;
        padding: 40px 60px;
        border-radius: 15px;
        text-align: center;
        box-shadow: 0 10px 40px rgba(0, 0, 0, 0.3);
    `;
    
    content.innerHTML = `
        <div class="spinner" style="margin: 0 auto 20px;"></div>
        <p style="font-size: 1.2em; color: #667eea; font-weight: 600; margin: 0;">${message}</p>
    `;
    
    overlay.appendChild(content);
    document.body.appendChild(overlay);
}

// 로딩 오버레이 제거
function hideLoadingOverlay() {
    const overlay = document.getElementById('loading-overlay');
    if (overlay) {
        overlay.remove();
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

// ==================== 건강 상태 체크 알림 ====================
let currentNotificationId = null;

// 알림 확인
async function checkNotifications() {
    if (!userIdValidated) {
        return;
    }
    
    const userId = document.getElementById('user-id').value.trim();
    if (!userId) {
        return;
    }
    
    try {
        const response = await fetch(`/get_notifications/${userId}`);
        const data = await response.json();
        
        if (data.error) {
            console.error('알림 조회 실패:', data.error);
            return;
        }
        
        if (data.notifications && data.notifications.length > 0) {
            // 가장 최근 알림 표시
            const latestNotification = data.notifications[0];
            showNotification(latestNotification);
        } else {
            // 알림이 없으면 배너 숨기기
            hideNotification();
        }
    } catch (error) {
        console.error('알림 확인 실패:', error);
    }
}

// 알림 표시
function showNotification(notification) {
    const banner = document.getElementById('notification-banner');
    const messageDiv = document.getElementById('notification-message');
    
    if (!banner || !messageDiv) return;
    
    currentNotificationId = notification._id;
    messageDiv.textContent = notification.message;
    banner.style.display = 'block';
    
    // 알림을 읽음으로 표시
    if (notification.status === 'pending') {
        markNotificationRead(notification._id);
    }
    
    // 챗봇 메시지로도 추가
    addChatMessage('bot', notification.message);
}

// 알림 숨기기
function hideNotification() {
    const banner = document.getElementById('notification-banner');
    if (banner) {
        banner.style.display = 'none';
    }
}

// 알림 닫기
function closeNotification() {
    hideNotification();
}

// 알림 읽음 표시
async function markNotificationRead(notificationId) {
    try {
        await fetch(`/mark_notification_read/${notificationId}`, {
            method: 'POST'
        });
    } catch (error) {
        console.error('알림 읽음 표시 실패:', error);
    }
}

// 알림 응답 표시
async function markNotificationResponded(notificationId) {
    try {
        await fetch(`/mark_notification_responded/${notificationId}`, {
            method: 'POST'
        });
        
        // 알림 배너 숨기기
        hideNotification();
    } catch (error) {
        console.error('알림 응답 표시 실패:', error);
    }
}

