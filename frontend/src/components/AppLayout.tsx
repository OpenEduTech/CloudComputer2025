import React, { useState } from 'react';
import { Layout, Menu, Dropdown, Avatar, Button, Drawer, Typography } from 'antd';
import {
  HomeOutlined,
  BookOutlined,
  LogoutOutlined,
  UserOutlined,
  MenuOutlined,
} from '@ant-design/icons';
import { useNavigate, useLocation, Outlet } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import type { MenuProps } from 'antd';

const { Header, Content, Footer } = Layout;
const { Text } = Typography;

/**
 * AppLayout component
 * Provides consistent layout with navigation menu, header, and content area
 * Features:
 * - Top navigation bar with logo and menu items
 * - User profile dropdown with logout option
 * - Responsive sidebar for mobile
 * - Breadcrumb navigation
 */
export const AppLayout: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { user, logout } = useAuth();
  const [mobileDrawerVisible, setMobileDrawerVisible] = useState(false);

  // Handle logout
  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  // Menu items for navigation
  const menuItems: MenuProps['items'] = [
    {
      key: '/',
      icon: <HomeOutlined />,
      label: '首页',
      onClick: () => {
        navigate('/');
        setMobileDrawerVisible(false);
      },
    },
    {
      key: '/mistakes',
      icon: <BookOutlined />,
      label: '错题本',
      onClick: () => {
        navigate('/mistakes');
        setMobileDrawerVisible(false);
      },
    },
  ];

  // User profile dropdown menu
  const userMenuItems: MenuProps['items'] = [
    {
      key: 'profile',
      icon: <UserOutlined />,
      label: '个人资料',
      onClick: () => navigate('/profile'),
    },
    {
      key: 'logout',
      icon: <LogoutOutlined />,
      label: '退出登录',
      onClick: handleLogout,
    },
  ];

  // Get current selected menu key based on location
  const getSelectedKey = () => {
    const path = location.pathname;
    if (path === '/') return '/';
    if (path.startsWith('/mistakes')) return '/mistakes';
    return '';
  };

  return (
    <Layout style={{ minHeight: '100vh' }}>
      {/* Desktop Header */}
      <Header
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '0 24px',
          background: '#001529',
          position: 'sticky',
          top: 0,
          zIndex: 1000,
        }}
      >
        {/* Logo and Menu for Desktop */}
        <div style={{ display: 'flex', alignItems: 'center', flex: 1 }}>
          {/* Mobile Menu Button */}
          <Button
            type="text"
            icon={<MenuOutlined style={{ color: '#fff', fontSize: '20px' }} />}
            onClick={() => setMobileDrawerVisible(true)}
            style={{
              display: 'none',
              marginRight: '16px',
            }}
            className="mobile-menu-button"
          />

          {/* Logo */}
          <div
            style={{
              color: '#fff',
              fontSize: '20px',
              fontWeight: 'bold',
              marginRight: '48px',
              cursor: 'pointer',
            }}
            onClick={() => navigate('/')}
          >
            智能学习系统
          </div>

          {/* Desktop Menu */}
          <Menu
            theme="dark"
            mode="horizontal"
            selectedKeys={[getSelectedKey()]}
            items={menuItems}
            style={{
              flex: 1,
              minWidth: 0,
              border: 'none',
            }}
            className="desktop-menu"
          />
        </div>

        {/* User Profile Dropdown */}
        <Dropdown menu={{ items: userMenuItems }} placement="bottomRight">
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              cursor: 'pointer',
              color: '#fff',
            }}
          >
            <Avatar icon={<UserOutlined />} style={{ marginRight: '8px' }} />
            <span>{user?.username || 'User'}</span>
          </div>
        </Dropdown>
      </Header>

      {/* Mobile Drawer */}
      <Drawer
        title="菜单"
        placement="left"
        onClose={() => setMobileDrawerVisible(false)}
        open={mobileDrawerVisible}
        className="mobile-drawer"
      >
        <Menu
          mode="vertical"
          selectedKeys={[getSelectedKey()]}
          items={menuItems}
          style={{ border: 'none' }}
        />
      </Drawer>

      {/* Main Content */}
      <Content style={{ padding: '12px', background: '#f0f2f5' }}>
        <div
          style={{
            background: '#fff',
            padding: '12px',
            minHeight: 'calc(100vh - 134px)',
            borderRadius: '8px',
          }}
        >
          <Outlet />
        </div>
      </Content>

      {/* Footer */}
      <Footer style={{ textAlign: 'center', background: '#f0f2f5', padding: '12px' }}>
        <Text style={{ fontSize: 'clamp(12px, 2vw, 14px)' }}>
          智能学习系统 ©{new Date().getFullYear()}
        </Text>
      </Footer>

      {/* Responsive CSS */}
      <style>{`
        @media (max-width: 768px) {
          .desktop-menu {
            display: none !important;
          }
          .mobile-menu-button {
            display: inline-block !important;
          }
        }
        @media (min-width: 769px) {
          .mobile-drawer {
            display: none;
          }
        }
        
        /* Ensure touch-friendly spacing on mobile */
        @media (max-width: 768px) {
          .ant-layout-header {
            padding: 0 12px !important;
          }
          .ant-card {
            margin-bottom: 12px;
          }
        }
      `}</style>
    </Layout>
  );
};
