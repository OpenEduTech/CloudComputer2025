import React, { useState } from 'react';
import { Form, Input, Button, Card, Typography, message, Select } from 'antd';
import { UserOutlined, MailOutlined, LockOutlined, BookOutlined } from '@ant-design/icons';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import type { RegisterData } from '../types/user';

const { Title, Text } = Typography;
const { Option } = Select;

/**
 * Register page
 * Allows new users to create an account
 * Requirements: 1.1, 1.2, 1.3, 1.4, 1.5
 */
export const Register: React.FC = () => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const { register } = useAuth();
  const navigate = useNavigate();

  /**
   * Handle form submission
   * Validates input and calls AuthContext.register()
   */
  const handleSubmit = async (values: RegisterData) => {
    setLoading(true);
    try {
      await register(values);
      message.success('注册成功！请登录');
      navigate('/login');
    } catch (error: any) {
      // Display user-friendly error message (already processed by API client interceptor)
      message.error(error.message || '注册失败，请重试');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ 
      display: 'flex', 
      justifyContent: 'center', 
      alignItems: 'center', 
      minHeight: '100vh',
      background: '#f0f2f5',
      padding: '20px'
    }}>
      <Card style={{ width: '100%', maxWidth: 400 }}>
        <div style={{ textAlign: 'center', marginBottom: 24 }}>
          <Title level={2}>创建账号</Title>
          <Text type="secondary">注册以开始学习</Text>
        </div>

        <Form
          form={form}
          name="register"
          onFinish={handleSubmit}
          layout="vertical"
          autoComplete="off"
        >
          <Form.Item
            name="username"
            label="用户名"
            rules={[
              { required: true, message: '请输入用户名' },
              { min: 3, message: '用户名至少需要3个字符' },
              { max: 50, message: '用户名不能超过50个字符' },
            ]}
          >
            <Input 
              prefix={<UserOutlined />} 
              placeholder="请输入用户名"
              size="large"
            />
          </Form.Item>

          <Form.Item
            name="email"
            label="邮箱"
            rules={[
              { required: true, message: '请输入邮箱' },
              { type: 'email', message: '请输入有效的邮箱地址' },
            ]}
          >
            <Input 
              prefix={<MailOutlined />} 
              placeholder="请输入邮箱"
              size="large"
            />
          </Form.Item>

          <Form.Item
            name="grade"
            label="年级"
            rules={[
              { required: true, message: '请选择年级' },
            ]}
            initialValue="初中"
          >
            <Select 
              placeholder="请选择年级"
              size="large"
              suffixIcon={<BookOutlined />}
            >
              <Option value="小学">小学</Option>
              <Option value="初中">初中</Option>
              <Option value="高中">高中</Option>
              <Option value="大学">大学</Option>
              <Option value="研究生">研究生</Option>
            </Select>
          </Form.Item>

          <Form.Item
            name="password"
            label="密码"
            rules={[
              { required: true, message: '请输入密码' },
              { min: 6, message: '密码至少需要6个字符' },
            ]}
          >
            <Input.Password 
              prefix={<LockOutlined />} 
              placeholder="请输入密码"
              size="large"
            />
          </Form.Item>

          <Form.Item
            name="confirmPassword"
            label="确认密码"
            dependencies={['password']}
            rules={[
              { required: true, message: '请确认密码' },
              ({ getFieldValue }) => ({
                validator(_, value) {
                  if (!value || getFieldValue('password') === value) {
                    return Promise.resolve();
                  }
                  return Promise.reject(new Error('两次输入的密码不一致'));
                },
              }),
            ]}
          >
            <Input.Password 
              prefix={<LockOutlined />} 
              placeholder="请确认密码"
              size="large"
            />
          </Form.Item>

          <Form.Item>
            <Button 
              type="primary" 
              htmlType="submit" 
              loading={loading}
              block
              size="large"
            >
              注册
            </Button>
          </Form.Item>

          <div style={{ textAlign: 'center' }}>
            <Text>已有账号？</Text>
            <Link to="/login">立即登录</Link>
          </div>
        </Form>
      </Card>
    </div>
  );
};
