'use client';

import { useState } from 'react';

export const WIDGET_REGISTRY = [
  { id: 'weather', label: '날씨 / THI', icon: '🌤️', defaultOn: true },
  { id: 'market', label: '시세 정보', icon: '💰', defaultOn: true },
  { id: 'notification', label: '알림 (발정/분만)', icon: '🔔', defaultOn: true },
  { id: 'financial', label: '경영 분석 차트', icon: '📊', defaultOn: true },
  { id: 'profitability', label: '출하 수익성 예측', icon: '📈', defaultOn: true },
  { id: 'estrus', label: '발정 알림 배너', icon: '💕', defaultOn: true },
  { id: 'calving', label: '분만 알림 배너', icon: '🍼', defaultOn: true },
  { id: 'stats', label: '핵심 통계', icon: '📈', defaultOn: true },
];

const WIDGETS_STORAGE_KEY = 'joolife-widgets';

/**
 * 위젯 ON/OFF 설정 훅.
 * localStorage에 영속화되며, WIDGET_REGISTRY 기본값과 merge됩니다.
 */
export function useWidgetSettings() {
  const [visible, setVisible] = useState(() => {
    const defaults = Object.fromEntries(WIDGET_REGISTRY.map((widget) => [widget.id, widget.defaultOn]));
    if (typeof window === 'undefined') return defaults;
    try {
      const saved = localStorage.getItem(WIDGETS_STORAGE_KEY);
      if (saved) return { ...defaults, ...JSON.parse(saved) };
    } catch {}
    return defaults;
  });

  const toggle = (id) => {
    setVisible((prev) => {
      const next = { ...prev, [id]: !prev[id] };
      localStorage.setItem(WIDGETS_STORAGE_KEY, JSON.stringify(next));
      return next;
    });
  };

  return { visible, toggle };
}
