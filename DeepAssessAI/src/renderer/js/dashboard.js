
document.addEventListener('DOMContentLoaded', () => {

    // 状态管理
    let currentMaterial = null;
    let materials = [];
    let questionConfig = {
        multipleChoice: { enabled: true, count: 10 },
        fillBlank: { enabled: false, count: 5 },
        shortAnswer: { enabled: false, count: 3 }
    };
    
    document.getElementById('logoutBtn').addEventListener('click', function() {
        if (confirm('确定要退出登录吗？')) {
            // 清除所有存储
            localStorage.removeItem('currentUser');
            sessionStorage.removeItem('currentUser');
            
            // 跳转到登录页
            window.location.replace('login.html');
        }
    });
    
    // 初始化
    init();

    // 初始化函数
    async function init() {
        setupNavigation();
        setupFileImport();
        setupQuestionConfig();
        setupMaterialManagement();
        setupEventListeners();
        
        // 加载资料列表
        await loadMaterials();
        
        // 设置难度选择
        setupDifficultySelection();
    }

    // 设置难度选择
    function setupDifficultySelection() {
        const difficultyButtons = document.querySelectorAll('.difficulty-btn');
        difficultyButtons.forEach(button => {
            button.addEventListener('click', function() {
                // 移除所有按钮的active类
                difficultyButtons.forEach(btn => btn.classList.remove('active'));
                
                // 给当前点击的按钮添加active类
                this.classList.add('active');
            });
        });

        // 题目类型切换功能
        const multipleChoiceToggle = document.getElementById('multipleChoiceToggle');
        const shortAnswerToggle = document.getElementById('shortAnswerToggle');
        
        const multipleChoiceCount = document.getElementById('multipleChoiceCount');
        const shortAnswerCount = document.getElementById('shortAnswerCount');

        // 选择题切换
        if (multipleChoiceToggle) {
            multipleChoiceToggle.addEventListener('change', function() {
                if (multipleChoiceCount) {
                    multipleChoiceCount.disabled = !this.checked;
                }
            });
        }
        
        // 简答题切换
        if (shortAnswerToggle) {
            shortAnswerToggle.addEventListener('change', function() {
                if (shortAnswerCount) {
                    shortAnswerCount.disabled = !this.checked;
                }
            });
        }
    }

    // 设置导航切换
    function setupNavigation() {
        const navLinks = document.querySelectorAll('.nav-link');
        navLinks.forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const page = link.dataset.page;
                
                // 移除所有active类
                navLinks.forEach(l => l.classList.remove('active'));
                // 添加当前active类
                link.classList.add('active');
                
                // 切换页面内容
                switchPage(page);
            });
        });
    }

    // 页面切换逻辑
    function switchPage(page) {
        // 隐藏所有页面内容
        document.querySelectorAll('.page-content').forEach(content => {
            content.style.display = 'none';
        });
        
        // 显示目标页面
        const targetPage = document.getElementById(`${page}Page`);
        if (targetPage) {
            targetPage.style.display = 'block';
        } else {
            console.warn(`页面 ${page} 不存在`);
            // 默认显示资料管理页面
            document.getElementById('materialsPage').style.display = 'block';
        }
        
        // 根据页面加载数据
        switch(page) {
            case 'questions':
                loadQuestions();
                break;
            case 'errors':
                loadErrorRecords();
                break;
            case 'evaluation':
                loadEvaluationData();
                break;
        }
    }

    // 设置文件导入功能
    function setupFileImport() {
        const importBtn = document.getElementById('importBtn');
        const selectedFile = document.getElementById('selectedFile');
        
        if (importBtn) {
            importBtn.addEventListener('click', async (e) => {
                e.preventDefault();
                
                try {
                    // 调用Electron API打开文件对话框
                    const result = await window.electronAPI.openFileDialog();
                    
                    if (!result.canceled && result.filePaths.length > 0) {
                        const filePath = result.filePaths[0];
                        const fileName = filePath.split('\\').pop().split('/').pop();
                        selectedFile.textContent = fileName;
                        
                        // 保存文件路径到全局变量，供保存时使用
                        window.selectedFilePath = filePath;
                        
                        // 自动填充资料名称（使用文件名）
                        const materialNameInput = document.getElementById('materialName');
                        if (materialNameInput && !materialNameInput.value) {
                            const nameWithoutExt = fileName.replace(/\.[^/.]+$/, "");
                            materialNameInput.value = nameWithoutExt;
                        }
                    }
                } catch (error) {
                    console.error('打开文件对话框失败:', error);
                    showAlert('打开文件失败，请重试', 'error');
                }
            });
        }
    }

    // 设置题目配置
    function setupQuestionConfig() {
        const multipleChoiceToggle = document.getElementById('multipleChoiceToggle');
        const shortAnswerToggle = document.getElementById('shortAnswerToggle');
        
        const multipleChoiceCount = document.getElementById('multipleChoiceCount');
        const shortAnswerCount = document.getElementById('shortAnswerCount');

        // 初始化开关状态
        if (multipleChoiceToggle) multipleChoiceToggle.checked = questionConfig.multipleChoice.enabled;
        if (shortAnswerToggle) shortAnswerToggle.checked = questionConfig.shortAnswer.enabled;

        // 初始化数量输入
        if (multipleChoiceCount) multipleChoiceCount.value = questionConfig.multipleChoice.count;
        if (shortAnswerCount) shortAnswerCount.value = questionConfig.shortAnswer.count;

        // 更新输入框状态
        updateInputStates();

        // 绑定开关事件
        if (multipleChoiceToggle) {
            multipleChoiceToggle.addEventListener('change', (e) => {
                questionConfig.multipleChoice.enabled = e.target.checked;
                updateInputStates();
                saveQuestionConfig();
            });
        }

        if (shortAnswerToggle) {
            shortAnswerToggle.addEventListener('change', (e) => {
                questionConfig.shortAnswer.enabled = e.target.checked;
                updateInputStates();
                saveQuestionConfig();
            });
        }

        // 绑定数量输入事件
        if (multipleChoiceCount) {
            multipleChoiceCount.addEventListener('change', (e) => {
                const count = parseInt(e.target.value) || 0;
                questionConfig.multipleChoice.count = Math.min(50, Math.max(1, count));
                e.target.value = questionConfig.multipleChoice.count;
                saveQuestionConfig();
            });
        }

        if (shortAnswerCount) {
            shortAnswerCount.addEventListener('change', (e) => {
                const count = parseInt(e.target.value) || 0;
                questionConfig.shortAnswer.count = Math.min(20, Math.max(1, count));
                e.target.value = questionConfig.shortAnswer.count;
                saveQuestionConfig();
            });
        }

        function updateInputStates() {
            if (multipleChoiceCount) {
                multipleChoiceCount.disabled = !questionConfig.multipleChoice.enabled;
            }
            
            if (shortAnswerCount) {
                shortAnswerCount.disabled = !questionConfig.shortAnswer.enabled;
            }
        }
    }

    // 设置资料管理
    function setupMaterialManagement() {
        const saveMaterialBtn = document.getElementById('saveMaterialBtn');
        const newMaterialBtn = document.getElementById('newMaterialBtn');
        const generateQuestionsBtn = document.getElementById('generateQuestionsBtn');

        // 保存资料按钮
        if (saveMaterialBtn) {
            saveMaterialBtn.addEventListener('click', async () => {
                await saveMaterial();
            });
        }

        // 新建资料按钮
        if (newMaterialBtn) {
            newMaterialBtn.addEventListener('click', () => {
                resetMaterialForm();
            });
        }

        // 生成题目按钮
        if (generateQuestionsBtn) {
            generateQuestionsBtn.addEventListener('click', async () => {
                await generateQuestions();
            });
        }
    }

    // 设置其他事件监听器
    function setupEventListeners() {
        // 窗口大小调整
        window.addEventListener('resize', handleResize);
    }

    // 加载资料列表
    async function loadMaterials() {
        try {
            // 模拟API调用
            // 实际应该从主进程获取数据
            materials = [
                {
                    id: '1',
                    name: '计算机科学导论',
                    type: 'PDF',
                    createdAt: '2024-01-15',
                    fileSize: '2.5 MB'
                },
                {
                    id: '2',
                    name: '机器学习笔记',
                    type: 'Markdown',
                    createdAt: '2024-01-10',
                    fileSize: '1.2 MB'
                }
            ];
            
            renderMaterialsList();
            
            // 默认选择第一个资料
            if (materials.length > 0) {
                selectMaterial(materials[0].id);
            }
        } catch (error) {
            console.error('加载资料失败:', error);
            showAlert('加载资料失败', 'error');
        }
    }

    // 渲染资料列表
    function renderMaterialsList() {
        const materialsList = document.getElementById('materialsList');
        if (!materialsList) return;
        
        materialsList.innerHTML = '';
        
        materials.forEach(material => {
            const materialItem = document.createElement('div');
            materialItem.className = `material-item ${currentMaterial?.id === material.id ? 'active' : ''}`;
            materialItem.dataset.id = material.id;
            
            materialItem.innerHTML = `
                <div class="material-title">${material.name}</div>
                <div class="material-meta">${material.type} • ${material.fileSize} • 创建于：${material.createdAt}</div>
                <div class="material-actions">
                    <button class="btn-icon delete-material" data-id="${material.id}" title="删除">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            `;
            
            // 点击选择资料
            materialItem.addEventListener('click', (e) => {
                if (!e.target.closest('.btn-icon')) {
                    selectMaterial(material.id);
                }
            });
            
            // 删除按钮
            const deleteBtn = materialItem.querySelector('.delete-material');
            if (deleteBtn) {
                deleteBtn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    deleteMaterial(material.id);
                });
            }
            
            materialsList.appendChild(materialItem);
        });
    }

    // 选择资料
    function selectMaterial(materialId) {
        const material = materials.find(m => m.id === materialId);
        if (!material) return;
        
        currentMaterial = material;
        renderMaterialsList();
        
        // 更新表单显示当前资料信息
        const materialNameInput = document.getElementById('materialName');
        if (materialNameInput) {
            materialNameInput.value = material.name;
        }
        
        // 显示选中的文件信息
        const selectedFile = document.getElementById('selectedFile');
        if (selectedFile) {
            selectedFile.textContent = `${material.name}.${material.type.toLowerCase()}`;
        }
        
        // 加载该资料的配置
        loadMaterialConfig(materialId);
    }

    // 保存资料
    async function saveMaterial() {
        const materialName = document.getElementById('materialName')?.value?.trim();
        const filePath = window.selectedFilePath;
        
        if (!materialName) {
            showAlert('请输入资料名称', 'warning');
            return;
        }
        
        if (!filePath) {
            showAlert('请选择要导入的文件', 'warning');
            return;
        }
        
        try {
            // 模拟保存资料
            const newMaterial = {
                id: Date.now().toString(),
                name: materialName,
                type: getFileType(filePath),
                createdAt: new Date().toLocaleDateString('zh-CN'),
                fileSize: '1.0 MB', // 实际应该获取文件大小
                path: filePath
            };
            
            materials.push(newMaterial);
            renderMaterialsList();
            selectMaterial(newMaterial.id);
            
            showAlert('资料保存成功', 'success');
            
            // 重置表单
            resetMaterialForm();
            
        } catch (error) {
            console.error('保存资料失败:', error);
            showAlert('保存资料失败', 'error');
        }
    }

    // 删除资料
    async function deleteMaterial(materialId) {
        if (!confirm('确定要删除这个资料吗？')) {
            return;
        }
        
        try {
            materials = materials.filter(m => m.id !== materialId);
            
            if (currentMaterial?.id === materialId) {
                currentMaterial = null;
                resetMaterialForm();
            }
            
            renderMaterialsList();
            showAlert('资料删除成功', 'success');
            
        } catch (error) {
            console.error('删除资料失败:', error);
            showAlert('删除资料失败', 'error');
        }
    }

    // 获取题目生成配置
    // 获取题目生成配置
    function getQuestionGenerationConfig() {
        if (!currentMaterial) {
            throw new Error('请先选择或创建一个资料');
        }
        
        // 获取难度
        const activeDifficultyBtn = document.querySelector('.difficulty-btn.active');
        if (!activeDifficultyBtn) {
            throw new Error('请选择难度');
        }
        const difficulty = activeDifficultyBtn.dataset.difficulty;
        
        // 获取选择题配置
        const multipleChoiceToggle = document.getElementById('multipleChoiceToggle');
        const multipleChoiceCount = document.getElementById('multipleChoiceCount');
        let multipleChoiceNum = 0;
        if (multipleChoiceToggle && multipleChoiceToggle.checked) {
            multipleChoiceNum = parseInt(multipleChoiceCount?.value) || 0;
            if (multipleChoiceNum < 1) {
                throw new Error('选择题数量必须大于0');
            }
        }
        
        // 获取简答题配置
        const shortAnswerToggle = document.getElementById('shortAnswerToggle');
        const shortAnswerCount = document.getElementById('shortAnswerCount');
        let shortAnswerNum = 0;
        if (shortAnswerToggle && shortAnswerToggle.checked) {
            shortAnswerNum = parseInt(shortAnswerCount?.value) || 0;
            if (shortAnswerNum < 1) {
                throw new Error('简答题数量必须大于0');
            }
        }
        
        // 获取填空题配置（如果存在）
        const fillBlankToggle = document.getElementById('fillBlankToggle');
        const fillBlankCount = document.getElementById('fillBlankCount');
        let fillBlankNum = 0;
        if (fillBlankToggle && fillBlankToggle.checked) {
            fillBlankNum = parseInt(fillBlankCount?.value) || 0;
            if (fillBlankNum < 1) {
                throw new Error('填空题数量必须大于0');
            }
        }
        
        // 检查至少选择了一种题型
        if (multipleChoiceNum === 0 && shortAnswerNum === 0 && fillBlankNum === 0) {
            throw new Error('请至少启用一种题目类型');
        }
        
        // 计算各难度题目数量
        function calculateDifficultyDistribution(totalCount, difficultyLevel) {
            if (difficultyLevel === 'advanced') {
                // 如果是提高难度
                let easy = Math.floor(totalCount * 0.3); // 30%
                let medium = Math.floor(totalCount * 0.4); // 40%
                let hard = Math.floor(totalCount * 0.3); // 30%
                
                // 计算总和
                let sum = easy + medium + hard;
                
                // 调整数量使总和等于totalCount
                if (sum < totalCount) {
                    const diff = totalCount - sum;
                    
                    if (diff === 1) {
                        hard += 1;
                    } else if (diff === 2) {
                        hard += 1;
                        medium += 1;
                    }
                }
                
                // 返回难度分布对象
                const distribution = {};
                if (easy > 0) distribution["1"] = easy;
                if (medium > 0) distribution["3"] = medium;
                if (hard > 0) distribution["5"] = hard;
                
                return distribution;
            }
            
            // 基础难度：简单:中等:难 = 4:4:2
            let easy = Math.floor(totalCount * 0.4); // 40%
            let medium = Math.floor(totalCount * 0.4); // 40%
            let hard = Math.floor(totalCount * 0.2); // 20%
            
            // 计算总和
            let sum = easy + medium + hard;
            
            // 调整数量使总和等于totalCount
            if (sum < totalCount) {
                const diff = totalCount - sum;
                
                if (diff === 1) {
                    medium += 1;
                } else if (diff === 2) {
                    easy += 1;
                    medium += 1;
                }
            }
            
            // 返回难度分布对象
            const distribution = {};
            if (easy > 0) distribution["1"] = easy;
            if (medium > 0) distribution["3"] = medium;
            if (hard > 0) distribution["5"] = hard;
            
            return distribution;
        }
        
        // 构建配置对象
        const config = {
            username: getCurrentUsername(), // 获取当前用户名
            config: {}
        };
        
        // 选择题难度分布
        if (multipleChoiceNum > 0) {
            config.config.mcq = calculateDifficultyDistribution(multipleChoiceNum, difficulty);
        }
        
        // 简答题难度分布
        if (shortAnswerNum > 0) {
            config.config.short = calculateDifficultyDistribution(shortAnswerNum, difficulty);
        }
        
        // 填空题难度分布（如果需要）
        if (fillBlankNum > 0) {
            config.config.fill = calculateDifficultyDistribution(fillBlankNum, difficulty);
        }
        
        console.log('生成的题目配置:', JSON.stringify(config, null, 2));
        
        return config;
    }

    // 获取当前用户名
    function getCurrentUsername() {
        // 这里从localStorage或sessionStorage获取当前登录用户的用户名
        // 如果还没实现用户系统，可以先用默认值
        const currentUser = localStorage.getItem('currentUser');
        if (currentUser) {
            try {
                const user = JSON.parse(currentUser);
                return user.username || 'cxy';
            } catch (e) {
                return 'cxy';
            }
        }
        
        // 默认用户名（用于测试）
        return 'cxy';
    }

    // 显示加载状态
    function showLoading(message = '处理中...') {
        // 创建一个加载遮罩
        const loadingOverlay = document.createElement('div');
        loadingOverlay.id = 'loadingOverlay';
        loadingOverlay.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background-color: rgba(0, 0, 0, 0.5);
            display: flex;
            justify-content: center;
            align-items: center;
            z-index: 9999;
            flex-direction: column;
        `;
        
        const spinner = document.createElement('div');
        spinner.style.cssText = `
            width: 50px;
            height: 50px;
            border: 5px solid #f3f3f3;
            border-top: 5px solid #3498db;
            border-radius: 50%;
            animation: spin 1s linear infinite;
        `;
        
        const text = document.createElement('div');
        text.textContent = message;
        text.style.cssText = `
            color: white;
            margin-top: 20px;
            font-size: 16px;
        `;
        
        const style = document.createElement('style');
        style.textContent = `
            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
        `;
        
        document.head.appendChild(style);
        loadingOverlay.appendChild(spinner);
        loadingOverlay.appendChild(text);
        document.body.appendChild(loadingOverlay);
        
        return loadingOverlay;
    }

    // 隐藏加载状态
    function hideLoading(loadingOverlay) {
        if (loadingOverlay && loadingOverlay.parentNode) {
            loadingOverlay.parentNode.removeChild(loadingOverlay);
        }
    }

    // 生成题目 - 主要修改的函数
    async function generateQuestions() {
        let loadingOverlay = null;
        
        try {
            // 检查是否选择了资料
            if (!currentMaterial) {
                showAlert('请先选择或创建一个资料', 'warning');
                return;
            }
            
            // 检查是否有选择的文件路径
            const filePath = window.selectedFilePath;
            if (!filePath) {
                showAlert('请先选择要导入的文件', 'warning');
                return;
            }
            
            // 显示加载状态
            loadingOverlay = showLoading('正在上传文件...');
            
            // 1. 上传文件到缓存
            const uploadResult = await uploadFileToCache(filePath);
            console.log('文件上传结果:', uploadResult);

            // 更新加载状态
            loadingOverlay.querySelector('div:nth-child(2)').textContent = '正在生成题目...';
            
            // 2. 获取题目生成配置
            const config = getQuestionGenerationConfig();
            console.log('发送的题目生成配置:', config);
            
            // 3. 发送POST请求生成题目
            const API_ENDPOINT = 'http://localhost:8000/api/generate_batch';        

            // 发送POST请求到后端
            const response = await axios.post(API_ENDPOINT, config, {
                headers: {
                    'Content-Type': 'application/json',
                },
                timeout: 600000 // 30秒超时
            });
            console.log('697行正确');
            // 隐藏加载状态
            hideLoading(loadingOverlay);
            console.log('699行正确');
            console.log('生成题目响应:', response);
            // 检查响应
            if (response.status == 200 || response.status == 201) {
                const data = response.data;
                console.log("题目生成成功啦");
                // 生成成功，获取题目数据
                const questions = data.questions;
                const totalQuestions = questions.length;
                console.log("题目生成成功啦lala");
                console.log("生成的题目数据:", questions);
                console.log("生成的题目数量:", totalQuestions);
                showAlert(`成功生成 ${totalQuestions} 道题目`, 'success');
                
                // 保存到本地存储，用于question-view.html页面
                localStorage.setItem('currentQuestions', JSON.stringify(questions));
                localStorage.setItem('currentMaterial', JSON.stringify(currentMaterial));
                localStorage.setItem('activeNav', 'questions');
                localStorage.setItem('questionConfig', JSON.stringify(config));
                localStorage.setItem('setId', data.set_id); // 保存set_id
                
                // 等待1秒后跳转，让用户看到成功提示
                setTimeout(() => {
                    // 跳转到题目展示页面
                    window.location.href = 'question.html';
                }, 1000);
            }
            
        } catch (error) {
            // 隐藏加载状态
            if (loadingOverlay) {
                hideLoading(loadingOverlay);
            }
            
            console.error('生成题目失败:', error);
            
            // 显示错误信息
            let errorMessage = '生成题目失败';
            
            if (error.response) {
                // 后端返回的错误
                const serverError = error.response.data;
                errorMessage = serverError.detail || serverError.message || `服务器错误: ${error.response.status}`;
            } else if (error.request) {
                // 请求发出但没有响应
                errorMessage = '网络错误，请检查网络连接或API地址';
            } else if (error.message) {
                // 其他错误
                errorMessage = error.message;
            }
            
            showAlert(errorMessage, 'error');
        }
    }

    // 上传文件到缓存的函数
    async function uploadFileToCache(filePath) {
        try {
            // 获取用户名
            const username = getCurrentUsername();
            
            console.log('开始上传文件，路径:', filePath, '用户名:', username);
            
            // 从文件路径读取文件
            const file = await readFileFromPath(filePath);
            
            if (!file) {
                throw new Error('无法读取文件');
            }
            
            console.log('文件读取成功:', file.name, '大小:', file.size, '类型:', file.type);
            
            // 创建FormData对象 - 根据后端接口参数名调整
            const formData = new FormData();
            // formData.append('username', username);
            formData.append('file', file);
            const url = `http://localhost:8000/api/upload_to_cache?username=${username}`;
            
            // 打印FormData内容（调试用）
            console.log('FormData内容:');
            for (let pair of formData.entries()) {
                console.log(pair[0], pair[1]);
            }
            
            // 上传文件到缓存
            const UPLOAD_API = 'http://localhost:8000/api/upload_to_cache';
            console.log('上传到API:', UPLOAD_API);
            const response = await fetch(url, {
                method: 'POST',
                body: formData
            })
            
            
            console.log('文件上传成功:', response.data);
            return response.data;
            
        } catch (error) {
            console.error('上传文件失败:', error);
            
            // 更详细的错误信息
            if (error.response) {
                console.error('服务器响应:', error.response.data);
                console.error('响应状态:', error.response.status);
                console.error('响应头:', error.response.headers);
                
                const serverError = error.response.data;
                throw new Error(serverError.detail || serverError.message || `服务器错误: ${error.response.status}`);
            } else if (error.request) {
                console.error('请求已发送但无响应:', error.request);
                throw new Error('无法连接到服务器，请检查网络连接');
            } else {
                console.error('请求配置错误:', error.config);
                throw new Error(`请求配置错误: ${error.message}`);
            }
        }
    }

    // 从文件路径读取文件的函数（修复版）
    async function readFileFromPath(filePath) {
        try {
            console.log('尝试读取文件:', filePath);
            // 在Electron环境中使用特定API
            const fileBuffer = window.electronAPI.getFileData(filePath);
            const fileName = filePath.split('\\').pop().split('/').pop();
            const file = new File([fileBuffer], fileName);
            return file;
        } catch (error) {
            console.error('读取文件失败:', error);
            throw error;
        }
    }

// 获取当前用户名（确保返回正确的格式）
function getCurrentUsername() {
    // 尝试从多个来源获取用户名
    const sources = [
        () => {
            const currentUser = localStorage.getItem('currentUser');
            if (currentUser) {
                try {
                    const user = JSON.parse(currentUser);
                    return user.username || user.name || 'cxy';
                } catch (e) {
                    return null;
                }
            }
            return null;
        },
        () => {
            const loginInfo = sessionStorage.getItem('loginInfo');
            if (loginInfo) {
                try {
                    const info = JSON.parse(loginInfo);
                    return info.username || info.name || 'cxy';
                } catch (e) {
                    return null;
                }
            }
            return null;
        },
        () => {
            // 检查URL参数
            const urlParams = new URLSearchParams(window.location.search);
            return urlParams.get('username');
        },
        () => {
            // 检查是否有默认用户名存储
            return localStorage.getItem('username');
        }
    ];
    
    // 按顺序尝试各个来源
    for (const getUsername of sources) {
        try {
            const username = getUsername();
            if (username && username.trim()) {
                console.log('获取到用户名:', username);
                return username.trim();
            }
        } catch (e) {
            // 忽略错误，继续尝试下一个来源
        }
    }
    
    // 默认用户名
    console.warn('未找到用户名，使用默认值:cxy');
    return 'cxy';
}

    // 加载题目（示例函数）
    async function loadQuestions() {
        // 实现题目加载逻辑
        console.log('加载题目...');
    }

    // 加载错题记录（示例函数）
    async function loadErrorRecords() {
        // 实现错题记录加载逻辑
        console.log('加载错题记录...');
    }

    // 加载评估数据（示例函数）
    async function loadEvaluationData() {
        // 实现评估数据加载逻辑
        console.log('加载评估数据...');
    }

    // 重置资料表单
    function resetMaterialForm() {
        const materialNameInput = document.getElementById('materialName');
        const selectedFile = document.getElementById('selectedFile');
        
        if (materialNameInput) materialNameInput.value = '';
        if (selectedFile) selectedFile.textContent = '未选择文件';
        
        window.selectedFilePath = null;
        currentMaterial = null;
        
        // 更新资料列表选中状态
        renderMaterialsList();
    }

    // 加载资料配置
    function loadMaterialConfig(materialId) {
        // 这里应该从存储中加载该资料的配置
        // 暂时使用默认配置
        console.log(`加载资料 ${materialId} 的配置`);
    }

    // 保存题目配置
    function saveQuestionConfig() {
        // 这里应该将配置保存到存储中
        console.log('保存题目配置:', questionConfig);
        
        // 如果当前有选中的资料，保存到该资料的配置中
        if (currentMaterial) {
            // saveConfigToStorage(currentMaterial.id, questionConfig);
        }
    }

    // 辅助函数：获取文件类型
    function getFileType(filePath) {
        const ext = filePath.split('.').pop().toLowerCase();
        const typeMap = {
            'pdf': 'PDF',
            'txt': 'Text',
            'md': 'Markdown',
            'docx': 'Word',
            'doc': 'Word'
        };
        return typeMap[ext] || 'File';
    }

    // 辅助函数：显示提示消息
    function showAlert(message, type = 'info') {
        // 移除现有的提示
        const existingAlert = document.querySelector('.alert-message');
        if (existingAlert) {
            existingAlert.remove();
        }
        
        // 创建新的提示
        const alert = document.createElement('div');
        alert.className = `alert-message alert-${type}`;
        alert.innerHTML = `
            <span>${message}</span>
            <button class="alert-close">&times;</button>
        `;
        
        // 样式
        alert.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 15px 20px;
            background: ${type === 'error' ? '#f44336' : 
                         type === 'success' ? '#4CAF50' : 
                         type === 'warning' ? '#ff9800' : '#2196F3'};
            color: white;
            border-radius: 5px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.2);
            z-index: 1000;
            display: flex;
            align-items: center;
            justify-content: space-between;
            min-width: 300px;
            max-width: 400px;
            animation: slideIn 0.3s ease-out;
        `;
        
        // 关闭按钮
        const closeBtn = alert.querySelector('.alert-close');
        closeBtn.addEventListener('click', () => {
            alert.remove();
        });
        
        // 自动消失
        setTimeout(() => {
            if (alert.parentNode) {
                alert.style.animation = 'slideOut 0.3s ease-out';
                setTimeout(() => alert.remove(), 300);
            }
        }, 5000);
        
        document.body.appendChild(alert);
        
        // 添加动画样式
        if (!document.querySelector('#alert-animations')) {
            const style = document.createElement('style');
            style.id = 'alert-animations';
            style.textContent = `
                @keyframes slideIn {
                    from { transform: translateX(100%); opacity: 0; }
                    to { transform: translateX(0); opacity: 1; }
                }
                @keyframes slideOut {
                    from { transform: translateX(0); opacity: 1; }
                    to { transform: translateX(100%); opacity: 0; }
                }
            `;
            document.head.appendChild(style);
        }
    }

    // 窗口大小调整处理
    function handleResize() {
        // 可以在这里添加响应式布局调整
        console.log('窗口大小调整:', window.innerWidth, window.innerHeight);
    }

    // 导出函数供其他模块使用（如果需要）
    window.dashboard = {
        loadMaterials,
        saveMaterial,
        generateQuestions
    };
});