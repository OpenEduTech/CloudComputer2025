import streamlit as st
from backend.database_service import DBManager

class AuthView:
    def __init__(self):
        if 'auth_state' not in st.session_state:
            st.session_state.auth_state = {
                'is_authenticated': False,
                'user': None,
                'auth_mode': 'login'  # login or register
            }
    
    def render_login_form(self):
        """渲染登录表单"""
        with st.form(key='login_form'):
            st.subheader("用户登录")
            username = st.text_input("用户名", placeholder="请输入用户名")
            password = st.text_input("密码", type="password", placeholder="请输入密码")
            
            # 移除内层列，使用按钮布局
            login_button = st.form_submit_button("登录")
            
            if login_button:
                if not username or not password:
                    st.error("请输入用户名和密码")
                else:
                    try:
                        user = st.session_state.db.verify_user(username, password)
                        if user:
                            st.session_state.auth_state['is_authenticated'] = True
                            st.session_state.auth_state['user'] = user
                            st.success("登录成功！")
                            st.rerun()
                        else:
                            st.error("用户名或密码错误")
                    except Exception as e:
                        st.error(f"登录失败: {e}")
        
        # 注册按钮移到表单外
        if st.button("注册新用户"):
            st.session_state.auth_state['auth_mode'] = 'register'
            st.rerun()
    
    def render_register_form(self):
        """渲染注册表单"""
        with st.form(key='register_form'):
            st.subheader("用户注册")
            username = st.text_input("用户名", placeholder="请输入用户名")
            password = st.text_input("密码", type="password", placeholder="请输入密码")
            confirm_password = st.text_input("确认密码", type="password", placeholder="请再次输入密码")
            email = st.text_input("邮箱", placeholder="请输入邮箱")
            name = st.text_input("姓名 (可选)", placeholder="请输入您的姓名")
            
            # 移除内层列，使用按钮布局
            register_button = st.form_submit_button("注册")
            
            if register_button:
                if not username or not password or not confirm_password or not email:
                    st.error("请填写所有必填字段")
                elif password != confirm_password:
                    st.error("两次输入的密码不一致")
                else:
                    try:
                        user_id, message = st.session_state.db.create_user(username, password, email, name)
                        if user_id:
                            st.success(message)
                            st.info("注册成功！请使用新账号登录")
                            st.session_state.auth_state['auth_mode'] = 'login'
                            st.rerun()
                        else:
                            st.error(message)
                    except Exception as e:
                        st.error(f"注册失败: {e}")
        
        # 登录按钮移到表单外
        if st.button("已有账号？登录"):
            st.session_state.auth_state['auth_mode'] = 'login'
            st.rerun()
    
    def render_auth_interface(self):
        """渲染认证界面"""
        # 创建登录/注册界面
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.title("📚 学习效果评估与巩固智能体")
            st.markdown("---")
            
            if st.session_state.auth_state['auth_mode'] == 'login':
                self.render_login_form()
            else:
                self.render_register_form()
    
    def render_user_profile(self):
        """渲染用户信息和退出按钮"""
        with st.sidebar.expander("👤 用户中心", expanded=True):
            user = st.session_state.auth_state['user']
            st.write(f"**用户名**: {user.get('username')}")
            st.write(f"**邮箱**: {user.get('email')}")
            st.write(f"**角色**: {user.get('role', '用户')}")
            
            if st.button("退出登录"):
                st.session_state.auth_state['is_authenticated'] = False
                st.session_state.auth_state['user'] = None
                st.session_state.auth_state['auth_mode'] = 'login'
                # 清除相关会话状态
                for key in ['file_ready', 'exam_data', 'user_answers', 'grading_result']:
                    if key in st.session_state:
                        del st.session_state[key]
                st.rerun()

def render_auth_view():
    """渲染认证视图"""
    auth_view = AuthView()
    if not st.session_state.auth_state['is_authenticated']:
        auth_view.render_auth_interface()
        return False
    else:
        auth_view.render_user_profile()
        return True
