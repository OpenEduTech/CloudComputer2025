
import React from 'react';

interface IconProps {
  name: string;
  className?: string;
  fillColor?: string;
}

export const DisciplineIcon: React.FC<IconProps> = ({ name, className, fillColor = "#d1d5db" }) => {
  const icons: Record<string, React.ReactNode> = {
    // 美术学
    palette: (
      <svg viewBox="0 0 100 100" className={className}>
        <path d="M50 15C30 15 15 30 15 50s15 35 35 35c8 0 15-7 15-15 0-4-2-8-5-11-1-1-2-2-2-4 0-3 2-5 5-5h12c12 0 20-10 20-22 0-18-12-28-45-28z" fill={fillColor} />
        <circle cx="35" cy="45" r="6" fill="#ffffff" opacity="0.5" />
        <circle cx="50" cy="35" r="6" fill="#ffffff" opacity="0.5" />
        <circle cx="65" cy="45" r="6" fill="#ffffff" opacity="0.5" />
      </svg>
    ),
    // 计算机
    laptop: (
      <svg viewBox="0 0 100 100" className={className}>
        <rect x="20" y="25" width="60" height="42" rx="4" fill={fillColor} />
        <path d="M15 67h70l5 8H10z" fill={fillColor} opacity="0.8" />
        <rect x="35" y="35" width="30" height="20" fill="#ffffff" opacity="0.3" />
      </svg>
    ),
    // 化学
    beaker: (
      <svg viewBox="0 0 100 100" className={className}>
        <path d="M35 15h30v15L20 85h60L45 30V15z" fill={fillColor} />
        <path d="M30 65h40v15H30z" fill="#ffffff" opacity="0.2" />
      </svg>
    ),
    // 物理学 - 车
    car: (
      <svg viewBox="0 0 100 100" className={className}>
        <path d="M15 60h70l-8-22H23z" fill={fillColor} />
        <rect x="10" y="55" width="80" height="15" rx="5" fill={fillColor} />
        <circle cx="30" cy="70" r="10" fill="#4b5563" />
        <circle cx="70" cy="70" r="10" fill="#4b5563" />
      </svg>
    ),
    // 文学 - 书
    book: (
      <svg viewBox="0 0 100 100" className={className}>
        <rect x="25" y="20" width="50" height="60" rx="2" fill={fillColor} />
        <path d="M25 70h50" stroke="#ffffff" strokeWidth="4" opacity="0.4" />
        <path d="M25 55h50" stroke="#ffffff" strokeWidth="4" opacity="0.4" />
        <path d="M25 40h50" stroke="#ffffff" strokeWidth="4" opacity="0.4" />
      </svg>
    ),
    // 地理 - 地球仪
    globe: (
      <svg viewBox="0 0 100 100" className={className}>
        <circle cx="50" cy="45" r="30" fill={fillColor} />
        <path d="M30 85h40M50 75v10" stroke="#4b5563" strokeWidth="4" strokeLinecap="round" />
        <path d="M35 35c5 10 15 5 25 15" stroke="#ffffff" strokeWidth="3" opacity="0.4" fill="none" />
      </svg>
    ),
    // 生物 - 树
    tree: (
      <svg viewBox="0 0 100 100" className={className}>
        <path d="M50 15L20 45h60z" fill={fillColor} />
        <path d="M50 35L15 70h70z" fill={fillColor} opacity="0.8" />
        <rect x="45" y="70" width="10" height="15" fill="#78350f" />
      </svg>
    ),
    // 数学 - 尺
    scale: (
      <svg viewBox="0 0 100 100" className={className}>
        <path d="M20 80L80 80L20 20Z" fill={fillColor} />
        <path d="M30 80v-8M40 80v-8M50 80v-8M60 80v-8M70 80v-8" stroke="#ffffff" strokeWidth="2" opacity="0.5" />
      </svg>
    )
  };

  const map: Record<string, string> = {
    art: 'palette', palette: 'palette',
    computer: 'laptop', cpu: 'laptop', laptop: 'laptop',
    chemistry: 'beaker', beaker: 'beaker',
    physics: 'car', car: 'car', atom: 'car',
    literature: 'book', book: 'book',
    geography: 'globe', globe: 'globe',
    biology: 'tree', tree: 'tree', leaf: 'tree',
    math: 'scale', maths: 'scale', scale: 'scale'
  };

  const key = map[name.toLowerCase()] || 'book';
  return icons[key] || icons.book;
};
