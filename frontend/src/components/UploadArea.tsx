import React, { useState } from 'react';
import { Upload, message } from 'antd';
import { InboxOutlined } from '@ant-design/icons';
import type { UploadProps } from 'antd';
import * as materialApi from '../api/material';

const { Dragger } = Upload;

interface UploadAreaProps {
  onUploadSuccess: (result: { filename: string; content: string; content_length: number }) => void;
  onUploadError: (error: string) => void;
}

const UploadArea: React.FC<UploadAreaProps> = ({ onUploadSuccess, onUploadError }) => {
  const [uploading, setUploading] = useState(false);

  const handleUpload = async (file: File) => {
    console.log('🚀 handleUpload 被调用');
    console.log('📄 文件名:', file.name);
    console.log('📄 文件类型:', file.type);
    console.log('📄 文件大小:', file.size);
    
    setUploading(true);
    
    try {
      message.loading({ content: '正在上传并解析PDF...', key: 'upload', duration: 0 });
      
      console.log('🔄 调用API上传文件...');
      const result = await materialApi.uploadAndParseMaterial(file);
      console.log('✅ API调用成功，结果:', result);
      
      message.success({ content: `${file.name} 上传并解析成功`, key: 'upload' });
      
      console.log('📢 调用 onUploadSuccess 回调');
      onUploadSuccess(result);
    } catch (error: any) {
      console.error('❌ 上传失败:', error);
      console.error('❌ 错误详情:', error.response?.data || error.message);
      const errorMessage = error.message || '上传失败';
      message.error({ content: errorMessage, key: 'upload' });
      onUploadError(errorMessage);
    } finally {
      setUploading(false);
      console.log('🏁 上传流程结束');
    }
  };

  const uploadProps: UploadProps = {
    name: 'file',
    multiple: false,
    accept: '.pdf',
    showUploadList: true,
    beforeUpload: (file) => {
      console.log('🔍 beforeUpload 被调用');
      console.log('📄 文件名:', file.name);
      console.log('📄 文件类型:', file.type);
      console.log('📄 文件大小:', file.size);
      
      // Validate file type - 扩展文件名检查作为后备
      const isPDF = file.type === 'application/pdf' || file.name.toLowerCase().endsWith('.pdf');
      if (!isPDF) {
        console.error('❌ 文件类型验证失败');
        message.error('只能上传PDF文件！');
        return Upload.LIST_IGNORE;
      }

      // Validate file size (e.g., max 50MB)
      const isLt50M = file.size / 1024 / 1024 < 50;
      if (!isLt50M) {
        message.error('文件大小不能超过50MB！');
        return Upload.LIST_IGNORE;
      }

      console.log('✅ 文件验证通过，执行上传');
      handleUpload(file);
      
      return false; // Prevent automatic upload
    },
    customRequest: async ({ file, onSuccess, onError }) => {
      console.log('⚠️ customRequest 被调用（这不应该发生）:', (file as File).name);
    },
    onDrop: (e) => {
      console.log('Dropped files', e.dataTransfer.files);
    },
  };

  return (
    <Dragger {...uploadProps} disabled={uploading}>
      <p className="ant-upload-drag-icon">
        <InboxOutlined />
      </p>
      <p className="ant-upload-text">点击或拖拽PDF文件到此区域上传</p>
      <p className="ant-upload-hint">
        支持单个PDF文件上传，文件大小不超过50MB。上传后将自动解析内容。
      </p>
    </Dragger>
  );
};

export default UploadArea;
