'use client'

import { usePathname } from 'next/navigation'
import {
  LayoutDashboard,
  Users,
  Key,
  Layers,
  DollarSign,
  FileText,
  Settings,
  Sparkles,
  ArrowLeft,
} from 'lucide-react'
import { SidebarLayout } from '@/components/catalyst/sidebar-layout'
import {
  Sidebar,
  SidebarHeader,
  SidebarBody,
  SidebarFooter,
  SidebarSection,
  SidebarItem,
  SidebarLabel,
  SidebarDivider,
  SidebarHeading,
} from '@/components/catalyst/sidebar'
import { Avatar } from '@/components/catalyst/avatar'
import {
  Dropdown,
  DropdownButton,
  DropdownMenu,
  DropdownItem,
  DropdownLabel,
  DropdownDivider,
} from '@/components/catalyst/dropdown'

const navigation = [
  { name: '概览', href: '/admin', icon: LayoutDashboard },
  { name: '用户管理', href: '/admin/users', icon: Users },
  { name: 'API 密钥', href: '/admin/keys', icon: Key },
  { name: '渠道管理', href: '/admin/channels', icon: Layers },
  { name: '定价配置', href: '/admin/pricing', icon: DollarSign },
  { name: '调用日志', href: '/admin/logs', icon: FileText },
  { name: '系统设置', href: '/admin/settings', icon: Settings },
]

function AdminSidebar() {
  const pathname = usePathname()

  return (
    <Sidebar>
      <SidebarHeader>
        <SidebarItem href="/">
          <ArrowLeft data-slot="icon" className="size-5" />
          <SidebarLabel>返回主站</SidebarLabel>
        </SidebarItem>
        <SidebarDivider />
        <div className="flex items-center gap-3 px-2">
          <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
            <Sparkles className="w-4 h-4 text-white" />
          </div>
          <div>
            <p className="text-sm font-semibold text-zinc-900 dark:text-white">CAPE Admin</p>
            <p className="text-xs text-zinc-500">管理控制台</p>
          </div>
        </div>
      </SidebarHeader>

      <SidebarBody>
        <SidebarSection>
          <SidebarHeading>导航</SidebarHeading>
          {navigation.map((item) => {
            const Icon = item.icon
            const isCurrent = pathname === item.href ||
              (item.href !== '/admin' && pathname.startsWith(item.href))

            return (
              <SidebarItem key={item.name} href={item.href} current={isCurrent}>
                <Icon data-slot="icon" className="size-5" />
                <SidebarLabel>{item.name}</SidebarLabel>
              </SidebarItem>
            )
          })}
        </SidebarSection>
      </SidebarBody>

      <SidebarFooter>
        <Dropdown>
          <DropdownButton as={SidebarItem}>
            <Avatar
              src="/avatar.png"
              initials="AD"
              className="size-8 bg-zinc-900 text-white"
            />
            <SidebarLabel>管理员</SidebarLabel>
          </DropdownButton>
          <DropdownMenu anchor="top start" className="min-w-48">
            <DropdownItem href="/admin/settings">
              <Settings data-slot="icon" className="size-4" />
              <DropdownLabel>系统设置</DropdownLabel>
            </DropdownItem>
            <DropdownDivider />
            <DropdownItem href="/">
              <ArrowLeft data-slot="icon" className="size-4" />
              <DropdownLabel>退出管理</DropdownLabel>
            </DropdownItem>
          </DropdownMenu>
        </Dropdown>
      </SidebarFooter>
    </Sidebar>
  )
}

function MobileNavbar() {
  return (
    <div className="flex items-center gap-2 px-4">
      <div className="w-6 h-6 bg-blue-600 rounded flex items-center justify-center">
        <Sparkles className="w-3 h-3 text-white" />
      </div>
      <span className="font-semibold text-zinc-900 dark:text-white">CAPE Admin</span>
    </div>
  )
}

export default function AdminLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <SidebarLayout
      navbar={<MobileNavbar />}
      sidebar={<AdminSidebar />}
    >
      {children}
    </SidebarLayout>
  )
}
