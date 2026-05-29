import { NavLink, useLocation } from "react-router-dom"
import { Settings } from "lucide-react"

import { useAppStore } from "@/store"
import {
  SidebarGroup,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  useSidebar,
} from "@/components/shadcn/sidebar"

export function SystemStatusFooter() {
  const { llmProvider, llmModel } = useAppStore()
  const { state, isMobile, setOpenMobile } = useSidebar()
  const { pathname } = useLocation()
  const collapsed = state === "collapsed"

  return (
    <SidebarGroup className="sticky bottom-0 z-10 bg-[color-mix(in_oklch,var(--sidebar)_88%,transparent)] px-4 py-3 backdrop-blur-xl">
      <SidebarMenu>
        <SidebarMenuItem>
          <SidebarMenuButton
            asChild
            tooltip="Settings"
            isActive={pathname === "/settings"}
          >
            <NavLink
              aria-label="Settings"
              title="Settings"
              className="justify-center"
              to="/settings"
              onClick={() => { if (isMobile) setOpenMobile(false) }}
            >
              <Settings />
              {!collapsed && (
                <span className="min-w-0 truncate">
                  Settings
                  <span className="ml-2 text-xs font-normal text-text-tertiary">
                    {llmProvider} / {llmModel}
                  </span>
                </span>
              )}
              {collapsed && <span className="sr-only">Settings</span>}
            </NavLink>
          </SidebarMenuButton>
        </SidebarMenuItem>
      </SidebarMenu>
    </SidebarGroup>
  )
}
