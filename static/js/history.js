// 데이터 조회 페이지 전용 JavaScript

// 전역 변수
let currentUserId = '';
let userIdValidated = false;
let userIdValidationTimer = null;
let userData = null;

// 특징 이름 한글 변환 함수 (upload.js와 동일)
function translateFeatureName(englishName) {
    const featureMap = {
        'activity_score_move_every_hour': '매시간 활동 점수',
        'activity_inactive': '비활동 시간',
        'activity_cal_total': '총 활동 칼로리',
        'activity': '활동량',
        'activity_score': '활동 점수',
        'activity_move': '이동 활동',
        'activity_cal': '활동 칼로리',
        'heart_rate': '심박수',
        'heart_rate_avg': '평균 심박수',
        'heart_rate_max': '최대 심박수',
        'heart_rate_min': '최소 심박수',
        'resting_heart_rate': '안정 시 심박수',
        'steps': '걸음수',
        'step_count': '걸음수',
        'steps_total': '총 걸음수',
        'steps_avg': '평균 걸음수',
        'sleep': '수면 시간',
        'sleep_duration': '수면 시간',
        'sleep_total': '총 수면 시간',
        'sleep_deep': '깊은 수면',
        'sleep_light': '얕은 수면',
        'sleep_rem': 'REM 수면',
        'temperature': '체온',
        'body_temperature': '체온',
        'temp': '체온',
        'distance': '이동 거리',
        'distance_total': '총 이동 거리',
        'distance_walking': '걷기 거리',
        'distance_running': '달리기 거리',
        'flights_climbed': '계단 오르기',
        'active_energy': '활동 에너지',
        'basal_energy': '기초 대사량',
    };
    
    if (featureMap[englishName]) {
        return featureMap[englishName];
    }
    
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
    
    return englishName.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
}

// 페이지 로드 시 초기화
document.addEventListener('DOMContentLoaded', function() {
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
    
    // 차트 초기화
    initializeCharts();
    
    // 윈도우 리사이즈 시 차트 크기 조정
    let resizeTimer;
    window.addEventListener('resize', function() {
        clearTimeout(resizeTimer);
        resizeTimer = setTimeout(function() {
            const chartIds = [
                'health-bar-chart-container',
                'health-pie-chart-container',
                'anomaly-gauge-chart-container',
                'anomaly-bar-chart-container'
            ];
            chartIds.forEach(id => {
                const element = document.getElementById(id);
                if (element && element.querySelector('.plotly')) {
                    Plotly.Plots.resize(id);
                }
            });
        }, 250);
    });
    
    // 페이지 로드 완료 후 차트 크기 조정
    window.addEventListener('load', function() {
        setTimeout(function() {
            const chartIds = [
                'health-bar-chart-container',
                'health-pie-chart-container',
                'anomaly-gauge-chart-container',
                'anomaly-bar-chart-container'
            ];
            chartIds.forEach(id => {
                const element = document.getElementById(id);
                if (element && element.querySelector('.plotly')) {
                    Plotly.Plots.resize(id);
                }
            });
        }, 500);
    });
});

// 사용자 ID 검증
function validateUserId() {
    const userIdInput = document.getElementById('user-id');
    const userId = userIdInput.value.trim();
    const statusDiv = document.getElementById('user-id-status');
    const loadBtn = document.getElementById('load-data-btn');
    
    if (userIdValidationTimer) {
        clearTimeout(userIdValidationTimer);
    }
    
    if (!userId) {
        statusDiv.innerHTML = '<span class="status-error">⚠️ 사용자 ID를 입력해주세요</span>';
        userIdValidated = false;
        loadBtn.disabled = true;
        return;
    }
    
    if (!/^[a-zA-Z0-9_-]+$/.test(userId)) {
        statusDiv.innerHTML = '<span class="status-error">❌ 사용자 ID는 영문, 숫자, _, - 만 사용 가능합니다</span>';
        userIdValidated = false;
        loadBtn.disabled = true;
        return;
    }
    
    if (userId.length < 3) {
        statusDiv.innerHTML = '<span class="status-error">❌ 사용자 ID는 최소 3자 이상이어야 합니다</span>';
        userIdValidated = false;
        loadBtn.disabled = true;
        return;
    }
    
    userIdValidationTimer = setTimeout(async () => {
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
        loadBtn.disabled = false;
        localStorage.setItem('userId', userId);
    }, 500);
}

// 사용자 ID 입력 시 Enter 키 처리
function handleUserIdKeyPress(event) {
    if (event.key === 'Enter' && userIdValidated) {
        loadUserHistory();
    }
}

// 사용자 데이터 조회
async function loadUserHistory() {
    if (!userIdValidated) {
        alert('먼저 사용자 ID를 입력하고 확인해주세요.');
        return;
    }
    
    const userId = document.getElementById('user-id').value.trim();
    if (!userId) {
        alert('사용자 ID를 입력해주세요.');
        return;
    }
    
    currentUserId = userId;
    
    try {
        // 사용자 데이터 조회
        const response = await fetch(`/get_user/${userId}?limit=100`);
        const data = await response.json();
        
        if (data.error) {
            alert('데이터 조회 실패: ' + data.error);
            return;
        }
        
        userData = data.data;
        
        // 통계 표시
        await displayUserStats(userId);
        
        // 데이터 목록 표시
        displayDataList(data.data);
        
        // 차트 업데이트
        updateTimeSeriesChart(data.data);
        updateAnomalyChart(data.data);
        
        // 섹션 표시
        document.getElementById('stats-section').style.display = 'block';
        document.getElementById('data-list-section').style.display = 'block';
        document.getElementById('visualization-section').style.display = 'block';
        
    } catch (error) {
        alert('데이터 조회 실패: ' + error.message);
    }
}

// 사용자 통계 표시
async function displayUserStats(userId) {
    try {
        const response = await fetch(`/get_statistics/${userId}`);
        const stats = await response.json();
        
        const statsContainer = document.getElementById('statistics-content');
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
            <div class="stat-card">
                <h3>최대 이상 점수</h3>
                <div class="value">${(stats.max_anomaly_score || 0).toFixed(2)}</div>
            </div>
            <div class="stat-card">
                <h3>최소 이상 점수</h3>
                <div class="value">${(stats.min_anomaly_score || 0).toFixed(2)}</div>
            </div>
        `;
    } catch (error) {
        console.error('통계 조회 실패:', error);
    }
}

// 데이터 목록 표시
function displayDataList(data) {
    const dataListContainer = document.getElementById('data-list');
    
    if (!data || data.length === 0) {
        dataListContainer.innerHTML = '<p style="text-align: center; color: #666; padding: 20px;">저장된 데이터가 없습니다.</p>';
        return;
    }
    
    let html = '<div class="data-list">';
    
    data.forEach((log, index) => {
        const date = log.date || '날짜 없음';
        const timestamp = log.timestamp || '';
        const anomalyDetected = log.anomaly_detected ? '⚠️ 이상 감지' : '✅ 정상';
        const anomalyScore = log.anomaly_score ? log.anomaly_score.toFixed(3) : 'N/A';
        const feedback = log.chatbot_feedback || '피드백 없음';
        
        html += `
            <div class="data-item" id="data-item-${log._id}">
                <div class="data-item-header">
                    <h3>${date} ${timestamp ? '(' + timestamp.substring(0, 10) + ')' : ''}</h3>
                    <div style="display: flex; gap: 10px; align-items: center;">
                        <span class="anomaly-badge ${log.anomaly_detected ? 'anomaly' : 'normal'}">${anomalyDetected}</span>
                        <button onclick="deleteDataItem('${log._id}', '${date}')" class="btn-delete" style="background: #ef4444; color: white; border: none; padding: 6px 12px; border-radius: 6px; cursor: pointer; font-size: 0.9em; transition: all 0.2s;" onmouseover="this.style.background='#dc2626'" onmouseout="this.style.background='#ef4444'">
                            🗑️ 삭제
                        </button>
                    </div>
                </div>
                <div class="data-item-content">
                    <div class="data-item-row">
                        <label>이상 점수:</label>
                        <span>${anomalyScore}</span>
                    </div>
                    ${log.sensor_data && log.sensor_data.length > 0 ? `
                        <div class="data-item-row">
                            <label>센서 데이터:</label>
                            <span>${log.sensor_data.length}개 기록</span>
                        </div>
                    ` : ''}
                    <div class="data-item-row full-width">
                        <label>챗봇 피드백:</label>
                        <div class="feedback-text">${feedback}</div>
                    </div>
                </div>
            </div>
        `;
    });
    
    html += '</div>';
    dataListContainer.innerHTML = html;
}

// 데이터 삭제
async function deleteDataItem(documentId, date) {
    if (!confirm(`정말로 ${date}의 데이터를 삭제하시겠습니까?\n\n이 작업은 되돌릴 수 없습니다.`)) {
        return;
    }
    
    try {
        // documentId를 URL 인코딩
        const encodedId = encodeURIComponent(documentId);
        const response = await fetch(`/delete_user_data/${encodedId}`, {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        if (!response.ok) {
            const errorText = await response.text();
            console.error('삭제 실패 응답:', errorText);
            throw new Error(`서버 오류: ${response.status} ${response.statusText}`);
        }
        
        const result = await response.json();
        
        if (result.success) {
            // 삭제된 항목을 화면에서 제거
            const dataItem = document.getElementById(`data-item-${documentId}`);
            if (dataItem) {
                dataItem.style.transition = 'opacity 0.3s';
                dataItem.style.opacity = '0';
                setTimeout(() => {
                    dataItem.remove();
                    // 데이터 목록이 비어있으면 메시지 표시
                    const dataList = document.querySelector('.data-list');
                    if (dataList && dataList.children.length === 0) {
                        document.getElementById('data-list').innerHTML = '<p style="text-align: center; color: #666; padding: 20px;">저장된 데이터가 없습니다.</p>';
                    }
                }, 300);
            }
            
            // 통계 및 차트 업데이트
            const userId = document.getElementById('user-id').value.trim();
            if (userId) {
                await loadUserHistory();
            }
            
            alert('✅ 데이터가 삭제되었습니다.');
        } else {
            alert('❌ 삭제 실패: ' + (result.error || '알 수 없는 오류'));
        }
    } catch (error) {
        console.error('삭제 실패:', error);
        alert('❌ 삭제 중 오류가 발생했습니다: ' + error.message);
    }
}

// 차트 초기화
function initializeCharts() {
    if (typeof Plotly === 'undefined') {
        console.error('Plotly 라이브러리가 로드되지 않았습니다.');
        return;
    }
    
    const timeSeriesContainer = document.getElementById('timeseries-chart');
    if (timeSeriesContainer) {
        updateTimeSeriesChart([]);
    }
    
    const anomalyContainer = document.getElementById('anomaly-chart');
    if (anomalyContainer) {
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
    }
}

// 시계열 차트 업데이트 (원형/막대 그래프로 변경)
function updateTimeSeriesChart(data) {
    // chart-container를 찾거나, 없으면 timeseries-chart의 부모를 사용
    let chartContainer = document.getElementById('chart-container');
    if (!chartContainer) {
        const timeseriesChart = document.getElementById('timeseries-chart');
        if (timeseriesChart && timeseriesChart.parentElement) {
            chartContainer = timeseriesChart.parentElement;
        } else {
            return;
        }
    }
    
    // 데이터 준비 (일별 데이터)
    const dateMap = new Map();
    
    if (data && data.length > 0) {
        data.forEach(log => {
            const date = log.date || new Date().toISOString().split('T')[0];
            if (log.sensor_data && Array.isArray(log.sensor_data) && log.sensor_data.length > 0) {
                // 심박수 추출 (여러 필드명 지원)
                const heartRateValues = log.sensor_data.map(sd => {
                    return sd.heart_rate || sd.heartRate || sd.heart_rate_avg || sd.resting_heart_rate || 0;
                }).filter(v => v > 0);
                const avgHeartRate = heartRateValues.length > 0 
                    ? heartRateValues.reduce((a, b) => a + b, 0) / heartRateValues.length 
                    : 0;
                
                // 걸음수 추출 (여러 필드명 지원)
                const stepValues = log.sensor_data.map(sd => {
                    return sd.steps || sd.step_count || sd.steps_total || sd.stepCount || 0;
                }).filter(v => v > 0);
                const avgSteps = stepValues.length > 0 
                    ? stepValues.reduce((a, b) => a + b, 0) / stepValues.length 
                    : 0;
                
                if (!dateMap.has(date)) {
                    dateMap.set(date, { heartRates: [], steps: [] });
                }
                if (avgHeartRate > 0) {
                    dateMap.get(date).heartRates.push(avgHeartRate);
                }
                if (avgSteps > 0) {
                    dateMap.get(date).steps.push(avgSteps);
                }
            }
        });
    }
    
    const times = [];
    const heartRates = [];
    const steps = [];
    
    // 날짜순 정렬
    const sortedDates = Array.from(dateMap.keys()).sort();
    sortedDates.forEach(date => {
        const dayData = dateMap.get(date);
        times.push(date);
        
        // 심박수 계산
        const avgHR = dayData.heartRates.length > 0 
            ? Math.round(dayData.heartRates.reduce((a, b) => a + b, 0) / dayData.heartRates.length)
            : 0;
        heartRates.push(avgHR);
        
        // 걸음수 계산
        const avgStep = dayData.steps.length > 0 
            ? Math.round(dayData.steps.reduce((a, b) => a + b, 0) / dayData.steps.length)
            : 0;
        steps.push(avgStep);
    });
    
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
        
        // 막대 그래프
        const trace1 = {
            x: formattedTimes,
            y: heartRates,
            type: 'bar',
            name: '심박수',
            marker: {
                color: heartRates.map(hr => {
                    if (hr >= 100) return '#ff4757';
                    if (hr >= 60 && hr < 100) return '#2ed573';
                    return '#ffa502';
                }),
                line: { width: 1, color: '#fff' }
            },
            hovertemplate: '<b>심박수</b><br>날짜: %{x}<br>심박수: %{y} bpm<extra></extra>',
            text: heartRates.map((v, i) => {
                // 걸음수가 있는 경우 심박수 텍스트는 표시하지 않음 (겹침 방지)
                if (v > 0 && steps[i] > 0) return '';
                return v > 0 ? (v + ' bpm') : '';
            }),
            textposition: 'outside',
            textfont: { size: 11, color: '#333', weight: 'bold', family: 'Malgun Gothic, 맑은 고딕' }
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
            hovertemplate: '<b>걸음수</b><br>날짜: %{x}<br>걸음수: %{y:,.0f} 걸음<extra></extra>',
            text: steps.map((v, i) => {
                if (v === 0 || v === null || v === undefined) return '';
                const formatted = Math.round(v).toLocaleString('ko-KR');
                // 심박수와 걸음수가 모두 있는 경우, 걸음수만 표시
                if (heartRates[i] > 0 && v > 0) {
                    return formatted + ' 걸음';
                }
                return formatted + ' 걸음';
            }),
            textposition: steps.map((v, i) => {
                // 심박수와 걸음수가 모두 있으면 걸음수는 아래에 표시
                if (heartRates[i] > 0 && v > 0) return 'inside';
                return 'outside';
            }),
            textfont: { size: 11, color: '#333', weight: 'bold', family: 'Malgun Gothic, 맑은 고딕' }
        };
        
        // 원형 차트 (심박수 분포)
        const pieData = [
            { label: '정상 심박수', value: heartRates.filter(hr => hr >= 60 && hr < 100).length, color: '#2ed573' },
            { label: '높은 심박수', value: heartRates.filter(hr => hr >= 100).length, color: '#ff4757' },
            { label: '낮은 심박수', value: heartRates.filter(hr => hr < 60 && hr > 0).length, color: '#ffa502' }
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
        
        // 심박수 상태 판단
        const getHeartRateStatus = (hr) => {
            if (hr >= 100) return { text: '높음', color: '#ff4757', icon: '⚠️' };
            if (hr >= 60 && hr < 100) return { text: '정상', color: '#2ed573', icon: '✅' };
            if (hr > 0) return { text: '낮음', color: '#ffa502', icon: '⚠️' };
            return { text: '측정 없음', color: '#95a5a6', icon: '❌' };
        };
        
        const heartRateStatus = getHeartRateStatus(latestHeartRate);
        const stepStatus = latestSteps >= 5000 ? { text: '좋음', color: '#2ed573' } : 
                          latestSteps >= 3000 ? { text: '보통', color: '#ffa502' } : 
                          { text: '부족', color: '#ff4757' };
        
        // 그래프 섹션 HTML
        const summaryHTML = `
            <div style="width: 100%; margin-bottom: 40px;">
                <h3 style="font-size: 22px; font-weight: 700; color: #1a1a1a; margin-bottom: 25px; font-family: 'Malgun Gothic', '맑은 고딕'; padding-bottom: 15px; border-bottom: 2px solid #e8e8e8;">📊 건강 데이터 그래프</h3>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 30px; width: 100%;">
                    <div style="background: white; padding: 25px; border-radius: 12px; box-shadow: 0 2px 12px rgba(0,0,0,0.08); border: 1px solid #e8e8e8; width: 100%; height: 520px; display: flex; flex-direction: column; overflow: hidden;">
                        <div id="health-bar-chart-container" style="width: 100%; flex: 1; min-height: 0; overflow: hidden;"></div>
                    </div>
                    <div style="background: white; padding: 25px; border-radius: 12px; box-shadow: 0 2px 12px rgba(0,0,0,0.08); border: 1px solid #e8e8e8; width: 100%; height: 520px; display: flex; flex-direction: column; overflow: hidden;">
                        <div id="health-pie-chart-container" style="width: 100%; flex: 1; min-height: 0; overflow: hidden;"></div>
                    </div>
                </div>
            </div>
        `;
        
        // timeseries-chart를 비우고 새 내용 추가
        const timeseriesChart = document.getElementById('timeseries-chart');
        if (timeseriesChart) {
            timeseriesChart.innerHTML = summaryHTML;
        } else {
            chartContainer.innerHTML = summaryHTML;
        }
        
        const barLayout = {
            title: {
                text: '일별 건강 데이터 변화',
                font: { size: 20, color: '#1a1a1a', family: 'Malgun Gothic, 맑은 고딕', weight: 'bold' },
                x: 0.5,
                xanchor: 'center',
                pad: { t: 5, b: 15 }
            },
            xaxis: { 
                title: { text: '📅 날짜', font: { size: 14, family: 'Malgun Gothic, 맑은 고딕', weight: 'bold' } },
                showgrid: true,
                gridcolor: 'rgba(0, 0, 0, 0.08)',
                tickangle: -30,
                tickfont: { size: 12, color: '#555' }
            },
            yaxis: { 
                title: { text: '❤️ 심박수 (bpm)', font: { size: 14, family: 'Malgun Gothic, 맑은 고딕', weight: 'bold', color: '#ff6b6b' } },
                side: 'left',
                showgrid: true,
                gridcolor: 'rgba(255, 107, 107, 0.2)',
                tickfont: { size: 12, color: '#ff6b6b', weight: 'bold' }
            },
            yaxis2: { 
                title: { text: '👣 걸음수', font: { size: 14, family: 'Malgun Gothic, 맑은 고딕', weight: 'bold', color: '#4ecdc4' } },
                overlaying: 'y', 
                side: 'right',
                showgrid: false,
                tickfont: { size: 12, color: '#4ecdc4', weight: 'bold' }
            },
            hovermode: 'x unified',
            showlegend: true,
            legend: {
                x: 0.5,
                y: -0.15,
                xanchor: 'center',
                yanchor: 'top',
                orientation: 'h',
                bgcolor: 'rgba(255, 255, 255, 0.95)',
                bordercolor: '#ddd',
                borderwidth: 1,
                font: { size: 14, family: 'Malgun Gothic, 맑은 고딕', weight: 'bold' }
            },
            plot_bgcolor: '#ffffff',
            paper_bgcolor: 'white',
            autosize: false,
            margin: { l: 85, r: 110, t: 80, b: 130 },
            height: 450,
            barmode: 'group',
            width: null,
            bargap: 0.3,
            bargroupgap: 0.1
        };
        
        const pieLayout = {
            title: {
                text: '심박수 상태 분포',
                font: { size: 20, color: '#1a1a1a', family: 'Malgun Gothic, 맑은 고딕', weight: 'bold' },
                x: 0.5,
                xanchor: 'center',
                pad: { t: 5, b: 15 }
            },
            showlegend: true,
            legend: {
                x: 0.5,
                y: -0.08,
                xanchor: 'center',
                orientation: 'h',
                font: { size: 13, family: 'Malgun Gothic, 맑은 고딕', weight: '600' },
                itemwidth: 25,
                bgcolor: 'rgba(255,255,255,0.8)',
                bordercolor: '#e8e8e8',
                borderwidth: 1
            },
            paper_bgcolor: 'white',
            plot_bgcolor: '#ffffff',
            height: 450,
            autosize: false,
            margin: { t: 75, b: 120, l: 75, r: 75 },
            width: null
        };
        
        const config = {
            responsive: true,
            displayModeBar: true,
            displaylogo: false,
            modeBarButtonsToRemove: ['pan2d', 'lasso2d', 'select2d'],
            autosizable: false,
            useResizeHandler: true
        };
        
        // 컨테이너 크기 계산 후 차트 생성
        const createCharts = () => {
            const barContainer = document.getElementById('health-bar-chart-container');
            const pieContainer = document.getElementById('health-pie-chart-container');
            
            if (barContainer) {
                const rect = barContainer.getBoundingClientRect();
                const containerHeight = rect.height || barContainer.clientHeight || 450;
                const containerWidth = rect.width || barContainer.clientWidth;
                barLayout.height = Math.max(400, Math.floor(containerHeight * 0.95));
                barLayout.width = Math.floor(containerWidth * 0.98);
                Plotly.newPlot('health-bar-chart-container', [trace1, trace2], barLayout, config).then(() => {
                    requestAnimationFrame(() => {
                        Plotly.Plots.resize('health-bar-chart-container');
                        setTimeout(() => {
                            Plotly.Plots.resize('health-bar-chart-container');
                        }, 100);
                    });
                });
            }
            
            if (pieContainer && pieData.length > 0) {
                const rect = pieContainer.getBoundingClientRect();
                const containerHeight = rect.height || pieContainer.clientHeight || 450;
                const containerWidth = rect.width || pieContainer.clientWidth;
                pieLayout.height = Math.max(400, Math.floor(containerHeight * 0.95));
                pieLayout.width = Math.floor(containerWidth * 0.98);
                Plotly.newPlot('health-pie-chart-container', [pieTrace], pieLayout, config).then(() => {
                    requestAnimationFrame(() => {
                        Plotly.Plots.resize('health-pie-chart-container');
                        setTimeout(() => {
                            Plotly.Plots.resize('health-pie-chart-container');
                        }, 100);
                    });
                });
            } else if (pieContainer) {
                pieContainer.innerHTML = '<div style="text-align: center; padding: 40px; color: #999;">데이터가 없습니다.</div>';
            }
        };
        
        // DOM이 준비될 때까지 대기
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => {
                setTimeout(createCharts, 200);
            });
        } else {
            setTimeout(createCharts, 200);
        }
        
    } catch (error) {
        console.error('시계열 차트 생성 실패:', error);
        chartContainer.innerHTML = '<div class="chart-error">차트를 표시할 수 없습니다.<br>오류: ' + error.message + '</div>';
    }
}

// 이상 탐지 차트 업데이트 (게이지 + 막대 그래프로 변경)
function updateAnomalyChart(data) {
    // anomaly-chart를 찾거나, 없으면 chart-container를 사용
    let chartContainer = document.getElementById('anomaly-chart');
    if (!chartContainer) {
        const chartContainerParent = document.getElementById('chart-container');
        if (chartContainerParent) {
            chartContainer = chartContainerParent;
        } else {
            return;
        }
    }
    
    const times = [];
    const anomalyScores = [];
    let threshold = 0.01;
    
    if (data && data.length > 0) {
        data.forEach(log => {
            if (log.anomaly_score !== null && log.anomaly_score !== undefined) {
                const dateStr = log.date || new Date().toISOString().split('T')[0];
                times.push(dateStr);
                anomalyScores.push(parseFloat(log.anomaly_score) || 0);
                if (log.threshold) {
                    threshold = parseFloat(log.threshold) || 0.01;
                }
            }
        });
    }
    
    if (times.length === 0) {
        const today = new Date().toISOString().split('T')[0];
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
            title: { text: "현재 이상 점수", font: { size: 20, family: 'Malgun Gothic, 맑은 고딕', weight: 'bold' } },
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
            font: { color: "#333", family: 'Malgun Gothic, 맑은 고딕', size: 14 },
            height: 450,
            autosize: false,
            margin: { t: 60, b: 60, l: 60, r: 60 },
            width: null
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
            textfont: { size: 13, color: '#333', weight: 'bold', family: 'Malgun Gothic, 맑은 고딕' }
        };
        
        const barLayout = {
            title: {
                text: '일별 이상 탐지 점수',
                font: { size: 20, color: '#1a1a1a', family: 'Malgun Gothic, 맑은 고딕', weight: 'bold' },
                x: 0.5,
                xanchor: 'center',
                pad: { t: 5, b: 15 }
            },
            xaxis: { 
                title: { text: '📅 날짜', font: { size: 14, family: 'Malgun Gothic, 맑은 고딕', weight: 'bold' } },
                showgrid: true,
                gridcolor: 'rgba(0, 0, 0, 0.08)',
                tickangle: -30,
                tickfont: { size: 12, color: '#555' }
            },
            yaxis: { 
                title: { text: '이상 점수', font: { size: 14, family: 'Malgun Gothic, 맑은 고딕', weight: 'bold' } },
                showgrid: true,
                gridcolor: 'rgba(0, 0, 0, 0.08)',
                zeroline: true,
                tickfont: { size: 12, weight: 'bold' }
            },
            shapes: [{
                type: 'line',
                xref: 'paper',
                yref: 'y',
                x0: 0,
                y0: threshold,
                x1: 1,
                y1: threshold,
                line: { color: '#ff4757', width: 3, dash: 'dash' }
            }],
            annotations: [{
                xref: 'paper',
                yref: 'y',
                x: 0.95,
                y: threshold,
                text: `임계값: ${threshold.toFixed(3)}`,
                showarrow: true,
                arrowhead: 3,
                arrowsize: 1.5,
                arrowcolor: '#ff4757',
                bgcolor: 'rgba(255, 255, 255, 0.95)',
                bordercolor: '#ff4757',
                borderwidth: 2,
                font: { size: 11, color: '#ff4757', family: 'Malgun Gothic, 맑은 고딕', weight: 'bold' }
            }],
            paper_bgcolor: 'white',
            plot_bgcolor: '#ffffff',
            height: 450,
            autosize: false,
            margin: { t: 75, b: 120, l: 85, r: 110 },
            showlegend: false,
            width: null
        };
        
        // 그래프 섹션 HTML
        const summaryHTML = `
            <div style="width: 100%;">
                <h3 style="font-size: 22px; font-weight: 700; color: #1a1a1a; margin-bottom: 25px; font-family: 'Malgun Gothic', '맑은 고딕'; padding-bottom: 15px; border-bottom: 2px solid #e8e8e8;">📊 이상 탐지 그래프</h3>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 30px; width: 100%;">
                    <div style="background: white; padding: 25px; border-radius: 12px; box-shadow: 0 2px 12px rgba(0,0,0,0.08); border: 1px solid #e8e8e8; width: 100%; height: 520px; display: flex; flex-direction: column; overflow: hidden;">
                        <div id="anomaly-gauge-chart-container" style="width: 100%; flex: 1; min-height: 0; overflow: hidden;"></div>
                    </div>
                    <div style="background: white; padding: 25px; border-radius: 12px; box-shadow: 0 2px 12px rgba(0,0,0,0.08); border: 1px solid #e8e8e8; width: 100%; height: 520px; display: flex; flex-direction: column; overflow: hidden;">
                        <div id="anomaly-bar-chart-container" style="width: 100%; flex: 1; min-height: 0; overflow: hidden;"></div>
                    </div>
                </div>
            </div>
        `;
        
        chartContainer.innerHTML = summaryHTML;
        
        const config = {
            responsive: true,
            displayModeBar: true,
            displaylogo: false,
            modeBarButtonsToRemove: ['pan2d', 'lasso2d', 'select2d'],
            autosizable: false,
            useResizeHandler: true
        };
        
        // 컨테이너 크기 계산 후 차트 생성
        const createAnomalyCharts = () => {
            const gaugeContainer = document.getElementById('anomaly-gauge-chart-container');
            const barContainer = document.getElementById('anomaly-bar-chart-container');
            
            if (gaugeContainer) {
                const rect = gaugeContainer.getBoundingClientRect();
                const containerHeight = rect.height || gaugeContainer.clientHeight || 450;
                const containerWidth = rect.width || gaugeContainer.clientWidth;
                gaugeLayout.height = Math.max(400, Math.floor(containerHeight * 0.95));
                gaugeLayout.width = Math.floor(containerWidth * 0.98);
                Plotly.newPlot('anomaly-gauge-chart-container', gaugeData, gaugeLayout, config).then(() => {
                    requestAnimationFrame(() => {
                        Plotly.Plots.resize('anomaly-gauge-chart-container');
                        setTimeout(() => {
                            Plotly.Plots.resize('anomaly-gauge-chart-container');
                        }, 100);
                    });
                });
            }
            
            if (barContainer) {
                const rect = barContainer.getBoundingClientRect();
                const containerHeight = rect.height || barContainer.clientHeight || 450;
                const containerWidth = rect.width || barContainer.clientWidth;
                barLayout.height = Math.max(400, Math.floor(containerHeight * 0.95));
                barLayout.width = Math.floor(containerWidth * 0.98);
                Plotly.newPlot('anomaly-bar-chart-container', [barTrace], barLayout, config).then(() => {
                    requestAnimationFrame(() => {
                        Plotly.Plots.resize('anomaly-bar-chart-container');
                        setTimeout(() => {
                            Plotly.Plots.resize('anomaly-bar-chart-container');
                        }, 100);
                    });
                });
            }
        };
        
        // DOM이 준비될 때까지 대기
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => {
                setTimeout(createAnomalyCharts, 200);
            });
        } else {
            setTimeout(createAnomalyCharts, 200);
        }
        
    } catch (error) {
        console.error('이상 탐지 차트 생성 실패:', error);
        chartContainer.innerHTML = '<div class="chart-error">차트를 표시할 수 없습니다.<br>오류: ' + error.message + '</div>';
    }
}

