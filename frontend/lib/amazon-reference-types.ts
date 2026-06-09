export type AmazonDomain =
  | 'amazon.com'
  | 'amazon.ca'
  | 'amazon.co.uk'
  | 'amazon.de'
  | 'amazon.fr'
  | 'amazon.it'
  | 'amazon.es'
  | 'amazon.co.jp'
  | 'amazon.com.au'
  | string;

export type ReferenceUsage =
  | 'own_product'
  | 'authorized_exact_reference'
  | 'similar_product_layout_only'
  | 'public_analysis_only'
  | 'text_analysis_only'
  | 'do_not_use';

export type AmazonImageType =
  | 'main_image_clean'
  | 'compatibility'
  | 'dimension'
  | 'feature'
  | 'application'
  | 'package'
  | 'material'
  | 'lifestyle';

export type OverlayTextMode = 'none' | 'recommended' | 'custom';

export interface ParsedAmazonUrl {
  originalUrl: string;
  normalizedUrl?: string;
  asin?: string;
  domain?: string;
  amazonDomain?: AmazonDomain;
  isAmazonUrl: boolean;
  warnings: string[];
}

export interface SerpApiAmazonSearchRequest {
  keyword: string;
  amazonDomain: AmazonDomain;
  language?: string;
  page?: number;
  device?: 'desktop' | 'tablet' | 'mobile';
}

export interface SerpApiAmazonProductRequest {
  asin: string;
  amazonDomain: AmazonDomain;
  language?: string;
  device?: 'desktop' | 'tablet' | 'mobile';
}

export interface SerpApiAmazonSearchItem {
  position?: number;
  asin?: string;
  title?: string;
  link?: string;
  linkClean?: string;
  serpapiLink?: string;
  thumbnail?: string;
  brand?: string;
  rating?: number;
  reviews?: number;
  price?: string;
  extractedPrice?: number;
  sponsored?: boolean;
  badges?: string[];
  tags?: string[];
}

export interface SerpApiAmazonSearchNormalized {
  source: 'serpapi_amazon_search';
  query: string;
  amazonDomain: AmazonDomain;
  page: number;
  totalResults?: number;
  organicResults: SerpApiAmazonSearchItem[];
  productAds?: SerpApiAmazonSearchItem[];
  relatedSearches?: string[];
  raw?: unknown;
  warnings: string[];
}

export interface SerpApiAmazonProductNormalized {
  source: 'serpapi_amazon_product';
  asin?: string;
  amazonDomain: AmazonDomain;
  title?: string;
  brand?: string;
  description?: string;
  categories?: string[];
  productLink?: string;
  mainImage?: string;
  images?: string[];
  rating?: number;
  reviews?: number;
  price?: string;
  extractedPrice?: number;
  availability?: string;
  aboutItem?: string[];
  itemSpecifications?: Record<string, string>;
  productDetails?: Record<string, string>;
  productFeatures?: string[];
  productDescription?: string;
  variants?: unknown[];
  compareWithSimilar?: unknown[];
  relatedProducts?: unknown[];
  boughtTogether?: unknown[];
  reviewsInformation?: unknown;
  normalizedFacts?: Record<string, string>;
  raw?: unknown;
  warnings: string[];
}

export interface SimilarProductReference {
  id: string;
  url?: string;
  asin?: string;
  amazonDomain?: AmazonDomain;
  platform: 'amazon' | 'walmart' | 'ebay' | 'aliexpress' | 'manufacturer' | 'shopify' | 'other';
  referenceType: 'own_listing' | 'own_product' | 'authorized_supplier' | 'manufacturer_reference' | 'similar_product' | 'competitor';
  permissionStatus: 'own' | 'authorized' | 'public_analysis_only' | 'unknown';
  allowedUsage: ReferenceUsage;
  userNotes?: string;
  title?: string;
  thumbnail?: string;
  productData?: SerpApiAmazonProductNormalized;
}

export interface ManualReferenceData {
  title?: string;
  bullets?: string[];
  imageNotes?: string;
  url?: string;
}

export interface ConfirmedProductFacts {
  productName?: string;
  productCategory?: string;
  brand?: string;
  material?: string;
  color?: string;
  diameter?: string;
  thickness?: string;
  arborHole?: string;
  grit?: string;
  quantity?: string;
  packageIncludes?: string;
  compatibilityTarget?: string;
}

export interface ProductFactsCandidate extends ConfirmedProductFacts {}

export interface ReferenceInsights {
  categorySignals: string[];
  commonVisualPatterns: string[];
  commonImageTypes: AmazonImageType[];
  safeStyleHints: string[];
  safeCompositionHints: string[];
  buyerConcernHints: string[];
  overlayTextPatterns: string[];
  productFactsCandidates: Record<string, string[]>;
  riskyClaimsFound: string[];
  brandOrTrademarkRisks: string[];
  unsafeToCopy: string[];
  recommendedQuestionsForUser: string[];
  warnings: string[];
  analysisMode?: string;
  model?: string;
}

export interface AmazonImageRequest {
  imageType: AmazonImageType;
  overlayTextMode?: OverlayTextMode;
  confirmedFacts: ConfirmedProductFacts;
  similarProductReferences?: SimilarProductReference[];
  referenceInsights?: ReferenceInsights;
  productReferenceImageNote?: string;
}

export interface PromptBundle {
  valid: boolean;
  imageType?: AmazonImageType;
  overlayTextMode?: OverlayTextMode;
  promptEn?: string;
  promptCn?: string;
  negativePrompt?: string;
  source?: string;
  errors?: string[];
}

export interface ValidationResult {
  valid: boolean;
  errors: string[];
  warnings?: string[];
}
