'use client';

import { useState, useEffect, useCallback } from 'react';

const STORAGE_KEY = 'joolife-theme';
const DARK_CLASS = 'dark';

function applyTheme(theme) {
  document.documentElement.setAttribute('data-theme', theme);
  document.documentElement.classList.toggle(DARK_CLASS, theme === 'dark');
}

export function useTheme() {
  const [theme, setTheme] = useState('light');

  useEffect(() => {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved === 'dark' || saved === 'light') {
      setTheme(saved);
      applyTheme(saved);
    } else if (window.matchMedia('(prefers-color-scheme: dark)').matches) {
      setTheme('dark');
      applyTheme('dark');
    } else {
      applyTheme('light');
    }
  }, []);

  const toggleTheme = useCallback(() => {
    setTheme(prev => {
      const next = prev === 'light' ? 'dark' : 'light';
      localStorage.setItem(STORAGE_KEY, next);
      applyTheme(next);
      return next;
    });
  }, []);

  return { theme, toggleTheme };
}
