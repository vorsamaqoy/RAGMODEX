import {
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/shadcn/sidebar"

export function TeamSwitcher() {
  return (
    <SidebarMenu>
      <SidebarMenuItem>
        <SidebarMenuButton size="lg" className="pointer-events-none h-14 select-none rounded-xl px-2">
          <img
            src="/logo_ragmodex.png?v=20260524"
            alt="RAGMODEX"
            className="size-9 shrink-0 rounded-sm object-cover"
          />
          <div className="min-w-0 flex-1 text-left leading-tight">
            <span className="block truncate text-[15px] font-semibold tracking-[-0.01em]">
              RAGMODEX
            </span>
          </div>
        </SidebarMenuButton>
      </SidebarMenuItem>
    </SidebarMenu>
  )
}

