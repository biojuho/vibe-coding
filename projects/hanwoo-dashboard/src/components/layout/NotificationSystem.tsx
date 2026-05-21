"use client";

import React, { useState } from 'react';
import { Bell } from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Button } from "@/components/ui/button";

const DEFAULT_NOTIFICATION_TITLE = '알림 제목 없음';
const DEFAULT_NOTIFICATION_MESSAGE = '확인할 알림 내용을 불러오지 못했습니다.';

function normalizeSystemNotifications(initialNotifications) {
  if (!Array.isArray(initialNotifications)) return [];

  return initialNotifications
    .filter((notification) => notification && typeof notification === 'object')
    .map((notification, index) => ({
      ...notification,
      id: notification.id ?? `notification-${index + 1}`,
      type: ['alert', 'warning', 'info'].includes(notification.type) ? notification.type : 'info',
      title: typeof notification.title === 'string' && notification.title.trim().length > 0
        ? notification.title
        : DEFAULT_NOTIFICATION_TITLE,
      message: typeof notification.message === 'string' && notification.message.trim().length > 0
        ? notification.message
        : DEFAULT_NOTIFICATION_MESSAGE,
      time: typeof notification.time === 'string' ? notification.time : '',
      read: Boolean(notification.read),
    }));
}

export function NotificationSystem({ initialNotifications = [] } = {}) {
  const [notifications, setNotifications] = useState(() => normalizeSystemNotifications(initialNotifications));
  const unreadCount = notifications.filter((notification) => !notification.read).length;
  const notificationLabel = unreadCount > 0
    ? `알림 열기, 읽지 않은 알림 ${unreadCount}개`
    : '알림 열기';

  const markAsRead = (id) => {
    setNotifications((currentNotifications) => currentNotifications.map((notification) => (
      notification.id === id ? { ...notification, read: true } : notification
    )));
  };

  const markAllAsRead = () => {
    setNotifications((currentNotifications) => currentNotifications.map((notification) => ({ ...notification, read: true })));
  };

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant="outline"
          size="icon"
          className="relative"
          aria-label={notificationLabel}
          title={notificationLabel}
        >
          <Bell className="h-4 w-4" aria-hidden="true" />
          {unreadCount > 0 && (
            <span
              className="absolute -top-1 -right-1 h-3 w-3 rounded-full bg-red-500 animate-pulse"
              aria-hidden="true"
            />
          )}
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-80">
        <DropdownMenuLabel className="flex items-center justify-between">
          <span>알림 센터</span>
          {unreadCount > 0 && (
            <button
              type="button"
              onClick={markAllAsRead}
              className="text-xs font-normal text-blue-500 hover:text-blue-700"
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
                className={`cursor-pointer ${notification.read ? 'opacity-60' : 'bg-blue-50/50'}`}
                onClick={() => markAsRead(notification.id)}
              >
                <div className="flex w-full flex-col gap-1">
                  <div className="flex items-center justify-between">
                    <span className={`font-semibold ${notification.type === 'alert' ? 'text-red-500' : ''}`}>
                      {notification.title}
                    </span>
                    <span className="text-xs text-muted-foreground">{notification.time}</span>
                  </div>
                  <p className="text-sm text-gray-500">{notification.message}</p>
                </div>
              </DropdownMenuItem>
            ))
          )}
        </div>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
