// Product name, in one place (see backend/branding.py for the why; story and rules in
// brand/BRAND-CORE.md). Override with VITE_BRAND_NAME / VITE_BRAND_NAME_BN in the root .env.
export const BRAND_NAME = import.meta.env.VITE_BRAND_NAME || 'Urbora'
export const BRAND_NAME_BN = import.meta.env.VITE_BRAND_NAME_BN || 'উর্বরা'
export const BRAND_TAGLINE_BN = 'স্বপ্ন ফলুক'
