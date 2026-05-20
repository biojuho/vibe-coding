"use client";

import React, { useState } from 'react';
import { BellIcon } from 'lucide-react';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Button } from '@/components/ui/button';

export function NotificationSystem({ initialNotifications = [] } = {}) {
  const [notifications, setNotifications] = useState(initialNotifications);

  const unreadCount = notifications.filter((notification) => !notification.read).length;
  const notificationLabel = unreadCount > 0
    ? `알림 열기, 읽지 않은 알림 ${unreadCount}개`
    : '알림 열기';

  const markAsRead = (id) => {
    setNotifications(notifications.map((notification) => (
      notification.id === id ? { ...notification, read: true } : notification
    )));
  };

  const markAllAsRead = () => {
    setNotifications(notifications.map((notification) => ({ ...notification, read: true })));
  };

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant="ghost"
          size="icon"
          className="relative"
          aria-label={notificationLabel}
          title={notificationLabel}
        >
          <BellIcon className="h-5 w-5" aria-hidden="true" />
          {unreadCount > 0 && (
            <span
              className="absolute top-0 right-0 h-2 w-2 rounded-full bg-red-600 animate-pulse"
              aria-hidden="true"
            />
          )}
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-80">
        <DropdownMenuLabel className="flex items-center justify-between">
          <span>알림 ({unreadCount})</span>
          {unreadCount > 0 && (
            <button
              type="button"
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
