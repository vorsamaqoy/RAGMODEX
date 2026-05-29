import { NavLink, useLocation } from "react-router-dom"
import type { LucideIcon } from "lucide-react"

import {
  SidebarGroup,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  useSidebar,
} from "@/components/shadcn/sidebar"

export type NavItem = {
  title: string
  url: string
  icon: LucideIcon
  end?: boolean
}

export function NavMain({ items }: { items: NavItem[] }) {
  const { isMobile, setOpenMobile } = useSidebar()
  const { pathname } = useLocation()

  return (
    <SidebarGroup className="px-4 pt-2">
      <SidebarMenu className="gap-1.5">
        {items.map((item) => {
          const isActive = item.end
            ? pathname === item.url
            : pathname === item.url || pathname.startsWith(item.url + "/")

          return (
            <SidebarMenuItem key={item.title}>
              <SidebarMenuButton asChild tooltip={item.title} isActive={isActive}>
                <NavLink
                  to={item.url}
                  end={item.end}
                  onClick={() => { if (isMobile) setOpenMobile(false) }}
                >
                  <item.icon />
                  <span>{item.title}</span>
                </NavLink>
              </SidebarMenuButton>
            </SidebarMenuItem>
          )
        })}
      </SidebarMenu>
    </SidebarGroup>
  )
}
