import { moleculeImageUrl } from '../lib/api'

interface Props {
  smiles: string
  width?: number
  height?: number
  className?: string
}

export function MolImage({ smiles, width = 300, height = 200, className }: Props) {
  if (!smiles) return null
  return (
    <img
      src={moleculeImageUrl(smiles, width, height)}
      alt={smiles}
      width={width}
      height={height}
      className={className}
      style={{ imageRendering: 'auto', background: 'transparent' }}
    />
  )
}
