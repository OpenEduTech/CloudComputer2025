import React, { useState, useEffect } from 'react';
import { Card, Form, Select, Button, Typography, Space, message, Spin } from 'antd';
import { UserOutlined, BookOutlined, MailOutlined } from '@ant-design/icons';
import { getCurrentUser, updateUserGrade } from '../api/auth';
import type { User } from '../types/user';

const { Title, Text } = Typography;
const { Option } = Select;

/**
 * Profile page
 * Allows users to view and update their profile information
 */
export const Profile: React.FC = () => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(true);
  const [updating, setUpdating] = useState(false);
  const [user, setUser] = useState<User | null>(null);

  useEffect(() => {
    fetchUserInfo();
  }, []);

  const fetchUserInfo = async () => {
    try {
      setLoading(true);
      const userData = await getCurrentUser();
      setUser(userData);
      form.setFieldsValue({
        grade: userData.grade || '初中',
      });
    } catch (error: any) {
      message.error(error.message || '加载用户信息失败');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (values: { grade: string }) => {
    try {
      setUpdating(true);
      const updatedUser = await updateUserGrade(values.grade);
      setUser(updatedUser);
      message.success('年级更新成功！');
    } catch (error: any) {
      message.error(error.message || '更新失败，请重试');
    } finally {
      setUpdating(false);
    }
  };

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: '100px 0' }}>
        <Spin size="large" />
      </div>
    );
  }

  return (
    <div style={{ padding: '12px', maxWidth: 600, margin: '0 auto' }} className="fade-in">
      <Space direction="vertical" size="large" style={{ width: '100%' }}>
        <div>
          <Title level={2} style={{ fontSize: 'clamp(20px, 5vw, 30px)' }}>
            个人资料
          </Title>
          <Text type="secondary" style={{ fontSize: 'clamp(14px, 2vw, 16px)' }}>
            查看和管理您的账户信息
          </Text>
        </div>

        <Card>
          <Space direction="vertical" size="large" style={{ width: '100%' }}>
            {/* User Info Display */}
            <div>
              <Space direction="vertical" size="middle" style={{ width: '100%' }}>
                <div>
                  <Text type="secondary">
                    <UserOutlined /> 用户名
                  </Text>
                  <div style={{ marginTop: 8 }}>
                    <Text strong style={{ fontSize: 16 }}>
                      {user?.username}
                    </Text>
                  </div>
                </div>

                <div>
                  <Text type="secondary">
                    <MailOutlined /> 邮箱
                  </Text>
                  <div style={{ marginTop: 8 }}>
                    <Text strong style={{ fontSize: 16 }}>
                      {user?.email}
                    </Text>
                  </div>
                </div>
              </Space>
            </div>

            {/* Grade Update Form */}
            <div style={{ marginTop: 24 }}>
              <Text type="secondary" style={{ marginBottom: 16, display: 'block' }}>
                <BookOutlined /> 年级设置
              </Text>
              <Form
                form={form}
                onFinish={handleSubmit}
                layout="vertical"
              >
                <Form.Item
                  name="grade"
                  label="当前年级"
                  rules={[{ required: true, message: '请选择年级' }]}
                >
                  <Select 
                    placeholder="请选择年级"
                    size="large"
                  >
                    <Option value="小学">小学</Option>
                    <Option value="初中">初中</Option>
                    <Option value="高中">高中</Option>
                    <Option value="大学">大学</Option>
                    <Option value="研究生">研究生</Option>
                  </Select>
                </Form.Item>

                <Form.Item>
                  <Button 
                    type="primary" 
                    htmlType="submit" 
                    loading={updating}
                    size="large"
                    block
                  >
                    保存更改
                  </Button>
                </Form.Item>
              </Form>

              <Text type="secondary" style={{ fontSize: 12 }}>
                💡 提示：年级设置会影响系统为您生成的题目难度和内容
              </Text>
            </div>
          </Space>
        </Card>
      </Space>
    </div>
  );
};
