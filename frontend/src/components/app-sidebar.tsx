import { useQuery } from "@tanstack/react-query"
import { MessageSquare, FlaskConical, Layers, Search, BarChart3, Atom } from "lucide-react"

import { getHealth } from "@/lib/api"
import { useAppStore } from "@/store"
import { NavMain } from "@/components/nav-main"
import { SystemStatusFooter } from "@/components/nav-user"
import { TeamSwitcher } from "@/components/team-switcher"
// TODO: Repurpose NavProjects for Recent Predictions
// import { NavProjects } from "@/components/nav-projects"
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarHeader,
  SidebarRail,
} from "@/components/shadcn/sidebar"
import type React from "react"

const NAV_ITEMS = [
  { title: "Chat",       url: "/",           icon: MessageSquare, end: true },
  { title: "Prediction", url: "/predict",    icon: FlaskConical },
  { title: "Design",     url: "/design",     icon: Layers },
  { title: "Screening",  url: "/screening",  icon: Search },
  { title: "Evaluation", url: "/evaluate",   icon: BarChart3 },
  { title: "Visualizer", url: "/visualizer", icon: Atom },
]

export function AppSidebar(props: React.ComponentProps<typeof Sidebar>) {
  const setModelStatus = useAppStore(s => s.setModelStatus)
  const setLlmStatus = useAppStore(s => s.setLlmStatus)

  useQuery({
    queryKey: ["health"],
    queryFn: async () => {
      const h = await getHealth()
      setModelStatus({
        modelLoaded:  !!h.model_loaded,
        trainingData: !!h.training_data,
        modelName:    String(h.model_name ?? ""),
        nMolecules:   0,
      })
      setLlmStatus({
        provider: String(h.llm_provider ?? "groq"),
        model: String(h.llm_model ?? "llama-3.3-70b-versatile"),
        temperature: Number(h.temperature ?? 0.3),
      })
      return h
    },
    refetchInterval: 5000,
  })

  return (
    <Sidebar collapsible="icon" {...props}>
      <SidebarHeader>
        <TeamSwitcher />
      </SidebarHeader>
      <SidebarContent>
        <NavMain items={NAV_ITEMS} />
      </SidebarContent>
      <SidebarFooter>
        <SystemStatusFooter />
      </SidebarFooter>
      <SidebarRail />
    </Sidebar>
  )
}
