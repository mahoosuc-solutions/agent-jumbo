// web/lib/products.ts
import { getProducts, type Product } from './manifest'

export function getBuilderProducts(): Product[] {
  return getProducts().filter((p) => p.audience === 'builder' || p.audience === 'both')
}

export function getBusinessProducts(): Product[] {
  return getProducts().filter((p) => p.audience === 'business' || p.audience === 'both')
}

export type { Product }
