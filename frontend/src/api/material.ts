import apiClient from './client';

/**
 * Upload and parse a PDF material
 * @param file - PDF file to upload
 * @returns Promise with parsed content
 */
export const uploadAndParseMaterial = async (file: File): Promise<{
  filename: string;
  content: string;
  content_length: number;
}> => {
  try {
    console.log('🌐 API: 准备上传文件', file.name);
    const formData = new FormData();
    formData.append('file', file);
    
    console.log('🌐 API: 发送POST请求到 /api/v1/materials/upload');
    const response = await apiClient.post('/api/v1/materials/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    
    console.log('🌐 API: 收到响应', response.data);
    return response.data;
  } catch (error: any) {
    console.error('🌐 API: 请求失败', error);
    if (error.response?.data?.detail) {
      throw new Error(error.response.data.detail);
    }
    throw new Error('Material upload and parsing failed. Please try again.');
  }
};
