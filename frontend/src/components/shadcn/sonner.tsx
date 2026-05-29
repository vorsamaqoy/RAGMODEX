import { CircleCheck, Info, LoaderCircle, OctagonX, TriangleAlert } from "lucide-react"
import { Toaster as Sonner } from "sonner"

type ToasterProps = React.ComponentProps<typeof Sonner>

const Toaster = ({ ...props }: ToasterProps) => (
  <Sonner
    theme="light"
    position="bottom-right"
    toastOptions={{
      classNames: {
        toast:
          "!border-white/70 !bg-white/78 !text-text-primary !shadow-[0_22px_52px_rgb(8_8_8_/_0.12)] !backdrop-blur-xl !rounded-md !text-sm !font-medium",
        title:    "!text-text-primary !font-semibold",
        description: "!text-text-tertiary !text-xs",
        success:  "[&_[data-icon]]:!text-[var(--accent-green)]",
        error:    "[&_[data-icon]]:!text-[var(--accent-red)]",
        warning:  "[&_[data-icon]]:!text-[var(--accent-orange)]",
        info:     "[&_[data-icon]]:!text-[var(--accent-blue-deep)]",
      },
    }}
    icons={{
      success: <CircleCheck className="h-4 w-4" />,
      info:    <Info className="h-4 w-4" />,
      warning: <TriangleAlert className="h-4 w-4" />,
      error:   <OctagonX className="h-4 w-4" />,
      loading: <LoaderCircle className="h-4 w-4 animate-spin" />,
    }}
    {...props}
  />
)

export { Toaster }
