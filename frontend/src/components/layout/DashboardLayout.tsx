import { Fragment, type ReactNode } from "react"
import { useMutation, useQuery } from "@tanstack/react-query"
import { Link, useNavigate } from "react-router-dom"
import { Bot, Cpu, Database } from "lucide-react"
import type { LucideIcon } from "lucide-react"
import { toast } from "sonner"

import { AppSidebar } from "@/components/app-sidebar"
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "@/components/shadcn/breadcrumb"
import { Separator } from "@/components/shadcn/separator"
import {
  SidebarInset,
  SidebarProvider,
  SidebarTrigger,
} from "@/components/shadcn/sidebar"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/shadcn/select"
import { useAppStore } from "@/store"
import { getLlmCatalog, setLlmConfig } from "@/lib/api"

export type BreadcrumbEntry = { label: string; href?: string }

interface DashboardLayoutProps {
  children: ReactNode
  breadcrumbs: BreadcrumbEntry[]
}

export function DashboardLayout({ children, breadcrumbs }: DashboardLayoutProps) {
  const { modelLoaded, trainingData, llmProvider, llmModel, temperature, setLlmStatus } = useAppStore()
  const navigate = useNavigate()
  const llmQ = useQuery({
    queryKey: ["llm-catalog"],
    queryFn: getLlmCatalog,
    staleTime: 30000,
  })
  const llmMut = useMutation({
    mutationFn: ({ provider, model }: { provider: string; model: string }) => (
      setLlmConfig(provider, model, temperature)
    ),
    onSuccess: d => {
      setLlmStatus({ provider: d.provider, model: d.model, temperature })
      toast.success("LLM configuration saved")
    },
    onError: err => toast.error(String(err)),
  })

  const providers = llmQ.data?.providers ?? []
  const currentModels = providers.find(p => p.name === llmProvider)?.models ?? [llmModel]

  return (
    <SidebarProvider>
      <AppSidebar />
      <SidebarInset>
        <header
          className="grid h-[62px] shrink-0 grid-cols-[1fr_auto_1fr] items-center gap-3 px-3 pr-6 backdrop-blur-xl"
          style={{
            background:
              "transparent",
          }}
        >
          <div className="flex items-center gap-3">
            <SidebarTrigger className="-ml-1 text-text-tertiary hover:text-text-primary" />
            <Separator orientation="vertical" className="mx-1 h-4 bg-border-subtle" />
            <Breadcrumb>
            <BreadcrumbList>
              {breadcrumbs.map((crumb, i) => {
                const isLast = i === breadcrumbs.length - 1
                return (
                  <Fragment key={i}>
                    <BreadcrumbItem>
                      {isLast ? (
                        <BreadcrumbPage>{crumb.label}</BreadcrumbPage>
                      ) : (
                        <BreadcrumbLink asChild>
                          <Link to={crumb.href ?? "/"}>{crumb.label}</Link>
                        </BreadcrumbLink>
                      )}
                    </BreadcrumbItem>
                    {!isLast && <BreadcrumbSeparator />}
                  </Fragment>
                )
              })}
            </BreadcrumbList>
            </Breadcrumb>
          </div>
          <div className="hidden items-center justify-center rounded-[14px] bg-white/45 p-1 shadow-[inset_0_1px_0_rgb(255_255_255_/_0.70),0_0_0_1px_rgb(15_18_28_/_0.05)] backdrop-blur-xl md:flex">
            <StatusPill icon={Cpu} label="Model" ok={modelLoaded} onClick={() => navigate("/settings")} />
            <StatusPill icon={Database} label="Dataset" ok={trainingData} onClick={() => navigate("/settings")} />
            <Select
              value={`${llmProvider}::${llmModel}`}
              onValueChange={value => {
                const [provider, model] = value.split("::")
                setLlmStatus({ provider, model, temperature })
                llmMut.mutate({ provider, model })
              }}
            >
              <SelectTrigger
                className="ml-1 h-[38px] min-w-[210px] rounded-[11px] border border-[rgb(15_18_28_/_0.06)] bg-white/45 px-2.5 text-xs font-semibold text-text-primary shadow-none hover:bg-white/60"
                aria-label="LLM provider and model"
              >
                <span className="flex min-w-0 items-center gap-2">
                  <span className="flex size-6 shrink-0 items-center justify-center rounded-md bg-[rgb(59_137_255_/_0.10)]">
                    <Bot className="size-3.5 opacity-75" />
                  </span>
                  <SelectValue placeholder={`${llmProvider} / ${llmModel}`} />
                </span>
              </SelectTrigger>
              <SelectContent>
                {providers.length > 0 ? providers.map(provider => (
                  provider.models.map(model => (
                    <SelectItem key={`${provider.name}::${model}`} value={`${provider.name}::${model}`}>
                      {provider.name} / {model}
                    </SelectItem>
                  ))
                )) : currentModels.map(model => (
                  <SelectItem key={`${llmProvider}::${model}`} value={`${llmProvider}::${model}`}>
                    {llmProvider} / {model}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="ml-auto hidden items-center gap-3 md:flex">
            <button
              type="button"
              onClick={() => navigate("/settings")}
              className="inline-flex h-9 items-center gap-2 rounded-full bg-white/30 px-3 text-xs font-medium text-text-secondary shadow-[inset_0_1px_0_rgb(255_255_255_/_0.70),0_0_0_1px_rgb(15_18_28_/_0.05)] backdrop-blur-xl transition-colors hover:bg-white/55"
            >
              <span
                className="size-2 rounded-full"
                style={{ background: modelLoaded && trainingData ? "var(--brand-accent)" : "var(--accent-orange)", boxShadow: "0 0 0 3px oklch(66% 0.115 155 / 0.18)" }}
              />
              Engine {modelLoaded && trainingData ? "ready" : "setup"}
            </button>
            <div className="grid size-[34px] place-items-center rounded-full bg-gradient-to-br from-[#ffe9d6] to-[#ffd0b5] text-xs font-bold text-[#7a3b1f] shadow-[inset_0_1px_0_rgb(255_255_255_/_0.60),0_0_0_1px_rgb(15_18_28_/_0.06)]">
              AM
            </div>
          </div>
        </header>
        <div className="flex flex-1 flex-col overflow-auto">
          {children}
        </div>
      </SidebarInset>
    </SidebarProvider>
  )
}

function StatusPill({
  icon: Icon,
  label,
  ok,
  onClick,
}: {
  icon: LucideIcon
  label: string
  ok: boolean
  onClick: () => void
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="inline-flex h-[38px] min-w-[108px] items-center gap-2 rounded-[11px] border px-2.5 text-xs font-semibold shadow-none transition-colors hover:bg-white/60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[oklch(66%_0.115_155_/_0.28)]"
      style={{
        background: ok ? "oklch(92% 0.04 155 / 0.72)" : "rgb(255 255 255 / 0.45)",
        borderColor: "rgb(15 18 28 / 0.06)",
        color: "var(--text-primary)",
      }}
      title={ok ? `${label} loaded` : `Import ${label.toLowerCase()}`}
      aria-label={ok ? `${label} loaded` : `Import ${label.toLowerCase()}`}
    >
      <span
        className="flex size-6 items-center justify-center rounded-md"
        style={{ background: ok ? "oklch(66% 0.115 155 / 0.14)" : "rgb(15 18 28 / 0.045)" }}
      >
        <Icon className="size-3.5 opacity-75" />
      </span>
      <span className="min-w-0 truncate">{label}</span>
      <span
        aria-hidden="true"
        className="ml-auto size-2 rounded-full"
        style={{ background: ok ? "var(--accent-green)" : "rgb(8 8 8 / 0.22)" }}
      />
    </button>
  )
}
