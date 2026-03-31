"use client";

import React, { useState } from 'react';
import { BellIcon, CheckIcon } from 'lucide-react';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Button } from '@/components/ui/button';

export function NotificationSystem() {
  const [notifications, setNotifications] = useState([
    { id: 1, title: '발정 예정 알림', message: '암소 #1024 발정 예정일입니다.', type: 'alert', read: false, time: '10분 전' },
    { id: 2, title: '재고 경고', message: '배합사료 재고가 10% 미만입니다.', type: 'warning', read: false, time: '1시간 전' },
    { id: 3, title: '분만 완료', message: '암소 #0892 정상 분만 완료 (암송아지)', type: 'info', read: true, time: '어제' },
  ]);

  const unreadCount = notifications.filter(n => !n.read).length;

  const markAsRead = (id) => {
    setNotifications(notifications.map(n => 
      n.id === id ? { ...n, read: true } : n
    ));
  };

  const markAllAsRead = () => {
    setNotifications(notifications.map(n => ({ ...n, read: true })));
  };

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="icon" className="relative">
          <BellIcon className="h-5 w-5" />
          {unreadCount > 0 && (
            <span className="absolute top-0 right-0 h-2 w-2 rounded-full bg-red-600 animate-pulse" />
          )}
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-80">
        <DropdownMenuLabel className="flex items-center justify-between">
          <span>알림 ({unreadCount})</span>
          {unreadCount > 0 && (
            <button 
              onClick={markAllAsRead}
              className="text-xs text-blue-500 hover:text-blue-700 font-normal"
            >
              모두 읽음
            </button>
          )}
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        <div className="max-h-[300px] overflow-y-auto">
          {notifications.length === 0 ? (
            <div className="p-4 text-center text-sm text-gray-500">
              새로운 알림이 없습니다.
            </div>
          ) : (
            notifications.map((notification) => (
              <DropdownMenuItem 
                key={notification.id} 
                className={`flex flex-col items-start gap-1 p-3 cursor-pointer ${notification.read ? 'opacity-60' : 'bg-blue-50/50'}`}
                onClick={() => markAsRead(notification.id)}
              >
                <div className="flex w-full items-start justify-between">
                  <span className={`text-sm font-semibold ${
                    notification.type === 'alert' ? 'text-red-500' :
                    notification.type === 'warning' ? 'text-orange-500' : 'text-blue-500'
                  }`}>
                    {notification.title}
                  </span>
                  <span className="text-xs text-gray-400">{notification.time}</span>
                </div>
                <p className="text-sm text-gray-700 line-clamp-2">
                  {notification.message}
                </p>
              </DropdownMenuItem>
            ))
          )}
        </div>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
