import React from 'react';
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

const NOTIFICATIONS = [
  { id: 1, title: '발정 알림', message: '암소 302호의 발정이 예상됩니다.', time: '10분 전', type: 'urgent' },
  { id: 2, title: '분만 임박', message: '암소 105호의 분만 예정일이 3일 남았습니다.', time: '1시간 전', type: 'info' },
  { id: 3, title: '사료 재고', message: '농후사료 재고가 10% 미만입니다.', time: '어제', type: 'warning' },
];

export function NotificationSystem() {
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="outline" size="icon" className="relative">
          <Bell className="h-4 w-4" />
          <span className="absolute -top-1 -right-1 h-3 w-3 rounded-full bg-red-500 animate-pulse" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-80">
        <DropdownMenuLabel>알림 센터</DropdownMenuLabel>
        <DropdownMenuSeparator />
        {NOTIFICATIONS.map((n) => (
          <DropdownMenuItem key={n.id} className="cursor-pointer">
            <div className="flex flex-col gap-1">
              <div className="flex items-center justify-between">
                <span className={`font-semibold ${n.type === 'urgent' ? 'text-red-500' : ''}`}>{n.title}</span>
                <span className="text-xs text-muted-foreground">{n.time}</span>
              </div>
              <p className="text-sm text-gray-500">{n.message}</p>
            </div>
          </DropdownMenuItem>
        ))}
        <DropdownMenuSeparator />
        <DropdownMenuItem className="text-center justify-center text-blue-500">
          모든 알림 보기
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
