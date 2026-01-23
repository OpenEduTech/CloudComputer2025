import React from 'react';
import { Card, Skeleton, Space } from 'antd';

/**
 * Skeleton loader components for better loading states
 * Provides visual feedback while content is loading
 */

export const QuizSkeleton: React.FC = () => {
  return (
    <div style={{ maxWidth: 900, margin: '0 auto', padding: '12px' }}>
      <Space direction="vertical" size="large" style={{ width: '100%' }}>
        <Skeleton.Input active style={{ width: 300, height: 32 }} />
        <Skeleton.Input active style={{ width: '100%', height: 8 }} />
        
        {[1, 2, 3].map((i) => (
          <Card key={i}>
            <Skeleton active paragraph={{ rows: 4 }} />
          </Card>
        ))}
      </Space>
    </div>
  );
};

export const ResultsSkeleton: React.FC = () => {
  return (
    <div style={{ maxWidth: 1200, margin: '0 auto', padding: '12px' }}>
      <Card style={{ marginBottom: 24 }}>
        <Space direction="vertical" style={{ width: '100%' }} size="large">
          <Skeleton.Input active style={{ width: 200, height: 32 }} />
          <div style={{ display: 'flex', gap: 16 }}>
            <Skeleton.Input active style={{ width: 150, height: 80 }} />
            <Skeleton.Input active style={{ width: 150, height: 80 }} />
            <Skeleton.Input active style={{ width: 150, height: 80 }} />
          </div>
          <Skeleton active paragraph={{ rows: 2 }} />
        </Space>
      </Card>

      {[1, 2, 3].map((i) => (
        <Card key={i} style={{ marginBottom: 16 }}>
          <Skeleton active paragraph={{ rows: 3 }} />
        </Card>
      ))}
    </div>
  );
};

export const MistakeBookSkeleton: React.FC = () => {
  return (
    <div style={{ padding: '12px' }}>
      <Space direction="vertical" size="large" style={{ width: '100%' }}>
        <Skeleton.Input active style={{ width: 250, height: 32 }} />
        
        <Card>
          <Skeleton active paragraph={{ rows: 3 }} />
        </Card>

        <Card>
          <Skeleton active paragraph={{ rows: 2 }} />
        </Card>

        {[1, 2].map((i) => (
          <Card key={i} style={{ marginBottom: 16 }}>
            <Skeleton active paragraph={{ rows: 4 }} />
          </Card>
        ))}
      </Space>
    </div>
  );
};

export const HomeSkeleton: React.FC = () => {
  return (
    <div style={{ padding: '12px' }}>
      <Space direction="vertical" size="large" style={{ width: '100%' }}>
        <div>
          <Skeleton.Input active style={{ width: 300, height: 32, marginBottom: 8 }} />
          <Skeleton.Input active style={{ width: '100%', height: 16 }} />
        </div>

        <Card>
          <Skeleton active paragraph={{ rows: 2 }} />
        </Card>

        <div>
          <Skeleton.Input active style={{ width: 200, height: 24, marginBottom: 16 }} />
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: 16 }}>
            {[1, 2, 3].map((i) => (
              <Card key={i}>
                <Skeleton active paragraph={{ rows: 2 }} />
              </Card>
            ))}
          </div>
        </div>
      </Space>
    </div>
  );
};
