import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Card,
  Modal,
  Form,
  Input,
  InputNumber,
  Space,
  Typography,
  message,
  Spin,
} from 'antd';
import UploadArea from '../components/UploadArea';
import * as materialApi from '../api/material';
import * as quizApi from '../api/quiz';

const { Title, Paragraph } = Typography;

export const Home: React.FC = () => {
  const navigate = useNavigate();
  const [isModalVisible, setIsModalVisible] = useState(false);
  const [parsedContent, setParsedContent] = useState<string>('');
  const [filename, setFilename] = useState<string>('');
  const [generatingQuiz, setGeneratingQuiz] = useState(false);
  const [form] = Form.useForm();

  useEffect(() => {
    console.log('🔄 状态变化 - isModalVisible:', isModalVisible);
    console.log('🔄 状态变化 - filename:', filename);
    console.log('🔄 状态变化 - parsedContent长度:', parsedContent.length);
  }, [isModalVisible, filename, parsedContent]);

  const handleUploadSuccess = (result: { filename: string; content: string; content_length: number }) => {
    console.log('🎉 Home收到上传成功回调:', result);
    console.log('📄 文件名:', result.filename);
    console.log('📊 内容长度:', result.content_length);
    
    setParsedContent(result.content);
    setFilename(result.filename);
    
    form.setFieldsValue({
      title: result.filename.replace('.pdf', ''),
      count: 10,
    });
    
    message.success({
      content: `✅ ${result.filename} 上传成功！内容长度: ${result.content_length} 字符`,
      duration: 3,
      key: 'upload'
    });
    
    setIsModalVisible(true);
  };

  const handleUploadError = (error: string) => {
    console.error('❌ Home收到上传错误:', error);
  };

  const handleModalOk = async () => {
    try {
      const values = await form.validateFields();
      setGeneratingQuiz(true);

      const quiz = await quizApi.generateQuiz(
        parsedContent,
        values.title,
        values.count
      );

      message.success('测验生成成功！');
      setIsModalVisible(false);
      navigate(`/quiz/${quiz.id}`);
    } catch (error: any) {
      if (error.errorFields) {
        // Form validation error - don't show message
        return;
      }
      message.error(error.message || '生成测验失败');
    } finally {
      setGeneratingQuiz(false);
    }
  };

  const handleModalCancel = () => {
    setIsModalVisible(false);
    setParsedContent('');
    setFilename('');
  };

  return (
    <div style={{ padding: '12px' }} className="fade-in">
      <Space direction="vertical" size="large" style={{ width: '100%' }}>
        <div>
          <Title level={2} style={{ fontSize: 'clamp(20px, 5vw, 30px)' }}>
            上传学习资料
          </Title>
          <Paragraph style={{ fontSize: 'clamp(14px, 2vw, 16px)' }}>
            上传PDF文档，系统将自动解析并生成个性化测验
          </Paragraph>
        </div>

        <Card>
          <UploadArea onUploadSuccess={handleUploadSuccess} onUploadError={handleUploadError} />
        </Card>
      </Space>

      <Modal
        title="生成测验"
        open={isModalVisible}
        onOk={handleModalOk}
        onCancel={handleModalCancel}
        confirmLoading={generatingQuiz}
        okText="生成"
        cancelText="取消"
        centered
      >
        <Form
          form={form}
          layout="vertical"
          initialValues={{
            title: '',
            count: 10,
          }}
        >
          <Form.Item
            name="title"
            label="测验标题"
            rules={[
              { required: true, message: '请输入测验标题' },
              { min: 3, message: '标题至少需要3个字符' },
            ]}
          >
            <Input placeholder="请输入测验标题" style={{ minHeight: '44px' }} />
          </Form.Item>

          <Form.Item
            name="count"
            label="题目数量"
            rules={[
              { required: true, message: '请输入题目数量' },
              { type: 'number', min: 1, max: 50, message: '题目数量必须在1到50之间' },
            ]}
          >
            <InputNumber
              min={1}
              max={50}
              style={{ width: '100%', minHeight: '44px' }}
              placeholder="请输入题目数量"
            />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};
