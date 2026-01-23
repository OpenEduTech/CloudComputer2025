// 全局变量
let questions = [];
let currentQuestionIndex = 0;
let totalQuestions = 0;

// DOM元素
const questionContainer = document.getElementById('question-container');
const prevBtn = document.getElementById('prev-btn');
const nextBtn = document.getElementById('next-btn');
const currentIndexSpan = document.getElementById('current-index');
const totalCountSpan = document.getElementById('total-count');
const pageTitle = document.getElementById('page-title');
const usernameSpan = document.getElementById('username');
const userAvatar = document.getElementById('user-avatar');

// 页面加载时初始化
document.addEventListener('DOMContentLoaded', function() {
    console.log('页面加载完成');
    
    // 设置导航栏事件
    setupNavigationEvents();
    
    // 设置退出登录事件
    document.getElementById('logoutBtn').addEventListener('click', function() {
        if (confirm('确定要退出登录吗？')) {
            cleanupLocalStorage();
            localStorage.removeItem('currentUser');
            sessionStorage.removeItem('currentUser');
            window.location.replace('login.html');
        }
    });
    
    // 检查localStorage中的题目数据
    const questionsData = localStorage.getItem('currentQuestions');
    const materialData = localStorage.getItem('currentMaterial');
    const userData = localStorage.getItem('currentUser');
    
    console.log('从localStorage获取数据:');
    console.log('questionsData:', questionsData ? '有数据' : '无数据');
    console.log('materialData:', materialData ? '有数据' : '无数据');
    
    // 更新用户信息
    if (userData) {
        try {
            const user = JSON.parse(userData);
            usernameSpan.textContent = user.username || user.name || '用户';
            userAvatar.textContent = (user.username || user.name || '用').charAt(0);
        } catch (e) {
            console.error('解析用户数据失败:', e);
        }
    }
    
    if (questionsData) {
        try {
            const parsedQuestions = JSON.parse(questionsData);
            console.log('解析到的题目数据:', parsedQuestions);
            
            if (materialData) {
                try {
                    const material = JSON.parse(materialData);
                    pageTitle.textContent = `题目生成 - ${material.name || '未知资料'}`;
                } catch (e) {
                    console.error('解析资料数据失败:', e);
                }
            }
            
            // 使用传递的题目数据初始化
            initWithQuestions(parsedQuestions);
        } catch (e) {
            console.error('解析题目数据失败:', e);
            showErrorMessage('加载题目数据失败，请重新生成题目。');
        }
    } else {
        console.warn('没有找到题目数据');
        showErrorMessage('没有找到题目数据，请从资料管理页面生成题目。');
    }
    
    // 页面关闭时清理数据
    window.addEventListener('beforeunload', cleanupLocalStorage);
});

// 使用后端返回的题目数据初始化
function initWithQuestions(questionsData) {
    console.log('初始化题目数据:', questionsData);
    
    // 转换后端数据格式为前端格式
    questions = transformQuestionsData(questionsData);
    totalQuestions = questions.length;
    
    console.log('转换后的题目:', questions);
    console.log('题目数量:', totalQuestions);
    
    if (totalQuestions === 0) {
        showErrorMessage('没有找到有效的题目数据。');
        return;
    }
    
    // 初始化UI
    totalCountSpan.textContent = totalQuestions;
    currentQuestionIndex = 0;
    
    renderQuestion(currentQuestionIndex);
    updateNavigationButtons();
    
    // 添加事件监听
    prevBtn.addEventListener('click', goToPrevQuestion);
    nextBtn.addEventListener('click', goToNextQuestion);
    
    // 添加选择题点击事件委托
    document.addEventListener('click', handleOptionClick);
}

// 转换后端题目数据为前端格式
function transformQuestionsData(backendQuestions) {
    if (!backendQuestions || !Array.isArray(backendQuestions)) {
        console.error('无效的题目数据格式:', backendQuestions);
        return [];
    }
    
    return backendQuestions.map((q, index) => {
        // 根据后端返回的数据结构进行转换
        // 假设后端返回的数据包含：type, content, options, answer等字段
        const question = {
            id: q.id || index + 1,
            type: mapQuestionType(q.type),
            content: q.content || q.question || '无题目内容',
            answer: q.answer || '',
            userAnswer: null,
            difficulty: q.difficulty || 'unknown'
        };
        
        // 处理选择题选项
        if (question.type === "选择题" && q.options && Array.isArray(q.options)) {
            question.options = q.options;
            // 如果答案是索引，确保是数字
            if (typeof q.answer === 'number' || !isNaN(q.answer)) {
                question.answer = parseInt(q.answer);
            }
        }
        
        // 处理填空题
        if (question.type === "填空题" && typeof q.answer === 'string') {
            // 填空题不需要额外处理
        }
        
        // 处理简答题
        if (question.type === "简答题") {
            // 简答题不需要额外处理
        }
        
        return question;
    });
}

// 映射题目类型
function mapQuestionType(type) {
    const typeMap = {
        'mcq': '选择题',
        'multiple_choice': '选择题',
        'choice': '选择题',
        'fill_blank': '填空题',
        'blank': '填空题',
        'short': '简答题',
        'essay': '简答题'
    };
    
    return typeMap[type] || type || '未知题型';
}

// 渲染题目
function renderQuestion(index) {
    if (index < 0 || index >= totalQuestions) {
        console.error('无效的题目索引:', index);
        return;
    }
    
    const question = questions[index];
    console.log(`渲染第 ${index + 1} 题:`, question);
    
    currentIndexSpan.textContent = index + 1;
    
    let questionHTML = `
        <div class="question-header">
            <div class="question-title">第 ${index + 1} 题</div>
            <div class="question-type">${question.type}</div>
        </div>
        <div class="question-content">${question.content}</div>
    `;
    
    // 根据题目类型渲染不同内容
    if (question.type === "选择题") {
        questionHTML += renderMultipleChoice(question, index);
    } else if (question.type === "填空题") {
        questionHTML += renderFillInBlank(question, index);
    } else if (question.type === "简答题") {
        questionHTML += renderShortAnswer(question, index);
    } else {
        questionHTML += `<div class="unknown-type">未知题型，无法显示</div>`;
    }
    
    questionContainer.innerHTML = questionHTML;
    
    // 如果用户已回答过此题，恢复答案
    if (question.userAnswer !== null) {
        restoreUserAnswer(question, index);
    }
}

// 渲染选择题
function renderMultipleChoice(question, questionIndex) {
    if (!question.options || !Array.isArray(question.options)) {
        return '<div class="error">题目选项数据异常</div>';
    }
    
    let optionsHTML = '<div class="options-container">';
    
    question.options.forEach((option, index) => {
        optionsHTML += `
            <div class="option" data-index="${index}" data-question="${questionIndex}">
                <div class="option-label">${String.fromCharCode(65 + index)}</div>
                <div class="option-text">${option}</div>
            </div>
        `;
    });
    
    optionsHTML += '</div>';
    return optionsHTML;
}

// 渲染填空题
function renderFillInBlank(question, questionIndex) {
    return `
        <div class="fill-blank-container">
            <input type="text" class="blank-input" data-question="${questionIndex}" 
                    placeholder="请输入答案" value="${question.userAnswer || ''}">
        </div>
    `;
}

// 渲染简答题
function renderShortAnswer(question, questionIndex) {
    return `
        <div class="short-answer-container">
            <textarea class="answer-textarea" data-question="${questionIndex}" 
                        placeholder="请输入您的答案...">${question.userAnswer || ''}</textarea>
        </div>
    `;
}

// 恢复用户答案
function restoreUserAnswer(question, questionIndex) {
    if (question.type === "选择题") {
        const optionElement = document.querySelector(`.option[data-question="${questionIndex}"][data-index="${question.userAnswer}"]`);
        if (optionElement) {
            optionElement.classList.add('selected');
        }
    } else if (question.type === "填空题") {
        const inputElement = document.querySelector(`.blank-input[data-question="${questionIndex}"]`);
        if (inputElement) {
            inputElement.value = question.userAnswer;
        }
    } else if (question.type === "简答题") {
        const textareaElement = document.querySelector(`.answer-textarea[data-question="${questionIndex}"]`);
        if (textareaElement) {
            textareaElement.value = question.userAnswer;
        }
    }
}

// 处理选择题点击事件
function handleOptionClick(e) {
    if (e.target.closest('.option')) {
        const optionElement = e.target.closest('.option');
        const questionIndex = parseInt(optionElement.dataset.question);
        const optionIndex = parseInt(optionElement.dataset.index);
        
        // 清除同一题目其他选项的选中状态
        const options = document.querySelectorAll(`.option[data-question="${questionIndex}"]`);
        options.forEach(opt => opt.classList.remove('selected'));
        
        // 选中当前选项
        optionElement.classList.add('selected');
        
        // 保存答案
        if (questions[questionIndex]) {
            questions[questionIndex].userAnswer = optionIndex;
        }
    }
}

// 更新导航按钮状态
function updateNavigationButtons() {
    prevBtn.disabled = currentQuestionIndex === 0;
    nextBtn.disabled = currentQuestionIndex === totalQuestions - 1;
    
    // 如果是最后一题，改变按钮文本
    if (currentQuestionIndex === totalQuestions - 1) {
        nextBtn.textContent = '完成练习';
    } else {
        nextBtn.textContent = '下一题';
    }
}

// 前往上一题
function goToPrevQuestion() {
    if (currentQuestionIndex > 0) {
        saveCurrentAnswer();
        currentQuestionIndex--;
        renderQuestion(currentQuestionIndex);
        updateNavigationButtons();
    }
}

// 前往下一题或完成练习
function goToNextQuestion() {
    if (currentQuestionIndex < totalQuestions - 1) {
        saveCurrentAnswer();
        currentQuestionIndex++;
        renderQuestion(currentQuestionIndex);
        updateNavigationButtons();
    } else {
        // 如果是最后一题，点击后显示完成界面
        saveCurrentAnswer();
        showCompletionScreen();
    }
}

// 保存当前题目的答案
function saveCurrentAnswer() {
    const question = questions[currentQuestionIndex];
    if (!question) return;
    
    if (question.type == "选择题") {
        const selectedOption = document.querySelector(`.option.selected[data-question="${currentQuestionIndex}"]`);
        if (selectedOption) {
            question.userAnswer = parseInt(selectedOption.dataset.index);
        }
    }
    else if (question.type === "简答题") {
        const textareaElement = document.querySelector(`.answer-textarea[data-question="${currentQuestionIndex}"]`);
        if (textareaElement) {
            question.userAnswer = textareaElement.value.trim();
        }
    }
}

// 显示完成界面
function showCompletionScreen() {
    const answeredCount = getAnsweredCount();
    
    questionContainer.innerHTML = `
        <div class="completion-message">
            <div class="completion-icon">🎉</div>
            <h2 class="completion-title">练习完成！</h2>
            <p class="completion-text">
                您已完成所有题目！<br>
                本次练习共 ${totalQuestions} 道题，您已回答了 ${answeredCount} 题。
            </p>
            <div class="completion-buttons">
                <button class="submit-button" id="submit-btn">提交答案并查看评估</button>
                <button class="return-button" id="return-btn">返回主界面</button>
            </div>
        </div>
    `;
    
    // 隐藏导航栏
    document.querySelector('.question-navigation').style.display = 'none';
    
    // 提交按钮事件
    document.getElementById('submit-btn').addEventListener('click', function() {
        submitAnswers();
    });
    
    // 返回按钮事件
    document.getElementById('return-btn').addEventListener('click', function() {
        navigateToDashboard();
    });
}

// 提交答案到后端
function submitAnswers() {
    console.log('提交答案:', questions);
    
    // 收集用户答案
    const userAnswers = questions.map(q => ({
        questionId: q.id,
        type: q.type,
        content: q.content,
        userAnswer: q.userAnswer,
        correctAnswer: q.answer
    }));
    
    // 这里应该调用后端API提交答案
    // 暂时用模拟实现
    showAlert('答案已提交！系统正在评估您的练习结果...', 'success');
    
    // 模拟评估完成后跳转
    setTimeout(() => {
        // 保存评估结果到localStorage
        const evaluationResult = {
            total: totalQuestions,
            answered: getAnsweredCount(),
            correct: Math.floor(getAnsweredCount() * 0.8), // 模拟80%正确率
            score: Math.floor((getAnsweredCount() / totalQuestions) * 100)
        };
        
        localStorage.setItem('evaluationResult', JSON.stringify(evaluationResult));
        
        // 跳转到评估页面
        window.location.href = 'evaluation.html';
    }, 2000);
}

// 获取已回答题目数量
function getAnsweredCount() {
    return questions.filter(q => q.userAnswer !== null && q.userAnswer !== '').length;
}

// 显示错误信息
function showErrorMessage(message) {
    questionContainer.innerHTML = `
        <div class="error-message">
            <h2>⚠️ 加载失败</h2>
            <p>${message}</p>
            <button class="return-button" onclick="navigateToDashboard()" style="margin-top: 20px;">
                返回资料管理
            </button>
        </div>
    `;
    
    // 隐藏导航栏
    document.querySelector('.question-navigation').style.display = 'none';
}

// 清理本地存储
function cleanupLocalStorage() {
    const itemsToRemove = [
        'currentQuestions',
        'currentMaterial',
        'activeNav',
        'questionProgress'
    ];
    
    itemsToRemove.forEach(item => {
        localStorage.removeItem(item);
    });
    
    console.log('已清理localStorage中的练习数据');
}

// 导航回dashboard
function navigateToDashboard() {
    cleanupLocalStorage();
    window.location.href = 'dashboard.html';
}

// 设置导航栏点击事件
function setupNavigationEvents() {
    // 资料管理 - 返回dashboard
    document.getElementById('zlgl').addEventListener('click', function(e) {
        e.preventDefault();
        
        const hasUnsavedAnswers = questions.some(q => q.userAnswer !== null && q.userAnswer !== '');
        
        if (hasUnsavedAnswers) {
            const confirmLeave = confirm('您有未提交的答案，确定要离开吗？您的进度将丢失。');
            if (confirmLeave) {
                navigateToDashboard();
            }
        } else {
            navigateToDashboard();
        }
    });
    
    // 其他导航项暂时显示提示
    const otherNavItems = ['evaluation-nav', 'errors-nav', 'profile-nav'];
    otherNavItems.forEach(id => {
        document.getElementById(id).addEventListener('click', function(e) {
            e.preventDefault();
            alert('此功能正在开发中，暂时不可用');
        });
    });
    
    // 题目生成 - 重新开始练习
    document.getElementById('questions-nav').addEventListener('click', function(e) {
        e.preventDefault();
        const confirmRestart = confirm('要重新开始当前练习吗？');
        if (confirmRestart) {
            // 重置所有答案
            questions.forEach(q => q.userAnswer = null);
            currentQuestionIndex = 0;
            renderQuestion(currentQuestionIndex);
            updateNavigationButtons();
        }
    });
}

// 显示提示消息
function showAlert(message, type = 'info') {
    // 移除现有的提示
    const existingAlert = document.querySelector('.custom-alert');
    if (existingAlert) {
        existingAlert.remove();
    }
    
    // 创建提示元素
    const alertDiv = document.createElement('div');
    alertDiv.className = `custom-alert`;
    alertDiv.textContent = message;
    
    // 样式
    alertDiv.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 15px 25px;
        border-radius: 8px;
        color: white;
        font-weight: 500;
        z-index: 10000;
        animation: slideIn 0.3s ease-out;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        background-color: ${type === 'success' ? '#27ae60' : 
                            type === 'error' ? '#e74c3c' : 
                            type === 'warning' ? '#f39c12' : '#3498db'};
    `;
    
    // 添加动画样式
    const style = document.createElement('style');
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
    `;
    document.head.appendChild(style);
    
    document.body.appendChild(alertDiv);
    
    // 3秒后自动消失
    setTimeout(() => {
        alertDiv.style.animation = 'slideOut 0.3s ease-out';
        setTimeout(() => {
            if (alertDiv.parentNode) {
                alertDiv.parentNode.removeChild(alertDiv);
            }
        }, 300);
    }, 3000);
}

// 处理文本框和文本域的输入事件
document.addEventListener('input', function(e) {
    if (e.target.classList.contains('blank-input')) {
        const questionIndex = parseInt(e.target.dataset.question);
        if (questions[questionIndex]) {
            questions[questionIndex].userAnswer = e.target.value.trim();
        }
    } else if (e.target.classList.contains('answer-textarea')) {
        const questionIndex = parseInt(e.target.dataset.question);
        if (questions[questionIndex]) {
            questions[questionIndex].userAnswer = e.target.value.trim();
        }
    }
});