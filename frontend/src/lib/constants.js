import {
  Fence, Axe, IndianRupee, Construction, Wheat, Droplets, Landmark, MessageSquareWarning,
  Inbox, Search, FileSearch, Hourglass, Send, CircleCheckBig, Ban, Archive,
} from 'lucide-react'

export const CATEGORIES = [
  { value: 'public_space_encroachment', label: 'Public Space Encroachment', icon: Fence,
    hint: 'Illegal building or fencing on village land, roads, ponds or common areas.' },
  { value: 'illegal_tree_cutting', label: 'Illegal Tree Cutting', icon: Axe,
    hint: 'Cutting or selling of public trees without permission.' },
  { value: 'development_fund_misuse', label: 'Development Fund Misuse', icon: IndianRupee,
    hint: 'Work shown as done but not done, poor quality work, or missing funds.' },
  { value: 'road_drainage', label: 'Road and Drainage Problems', icon: Construction,
    hint: 'Broken roads, blocked drains, waterlogging or damaged culverts.' },
  { value: 'ration_distribution', label: 'Ration Distribution Irregularities', icon: Wheat,
    hint: 'Less ration, poor quality, shop closed or people wrongly turned away.' },
  { value: 'public_resource_misuse', label: 'Public Resource Misuse', icon: Droplets,
    hint: 'Private use of water tankers, community halls, street lights, etc.' },
  { value: 'corruption_governance', label: 'Corruption or Local Governance Issues', icon: Landmark,
    hint: 'Bribes, fake meetings, misuse of scheme lists or job cards.' },
  { value: 'other', label: 'Other Village Problems', icon: MessageSquareWarning,
    hint: 'Any other problem with public services in your village.' },
]
export const CATEGORY_MAP = Object.fromEntries(CATEGORIES.map((c) => [c.value, c]))

// Status colours always come with an icon and a text label (never colour alone).
export const STATUSES = {
  received: { label: 'Received', icon: Inbox, tone: 'bg-sky-50 text-sky-800 ring-sky-200' },
  under_review: { label: 'Under Review', icon: Search, tone: 'bg-indigo-50 text-indigo-800 ring-indigo-200' },
  evidence_verification: { label: 'Evidence Verification', icon: FileSearch, tone: 'bg-violet-50 text-violet-800 ring-violet-200' },
  action_in_progress: { label: 'Action in Progress', icon: Hourglass, tone: 'bg-amber-50 text-amber-900 ring-amber-200' },
  forwarded: { label: 'Forwarded to Relevant Authority', short: 'Forwarded', icon: Send, tone: 'bg-cyan-50 text-cyan-900 ring-cyan-200' },
  resolved: { label: 'Resolved', icon: CircleCheckBig, tone: 'bg-brand-50 text-brand-800 ring-brand-200' },
  rejected: { label: 'Rejected', icon: Ban, tone: 'bg-red-50 text-red-800 ring-red-200' },
  closed: { label: 'Closed', icon: Archive, tone: 'bg-slate-100 text-slate-700 ring-slate-300' },
}
export const STATUS_ORDER = Object.keys(STATUSES)

export const VERIFICATION = {
  pending: { label: 'Not yet verified', tone: 'bg-slate-100 text-slate-700 ring-slate-300' },
  verified: { label: 'Verified', tone: 'bg-brand-50 text-brand-800 ring-brand-200' },
  unverified: { label: 'Could not be verified', tone: 'bg-red-50 text-red-800 ring-red-200' },
  needs_more_info: { label: 'Needs more information', tone: 'bg-amber-50 text-amber-900 ring-amber-200' },
}

export const STATES = [
  'Andaman and Nicobar Islands', 'Andhra Pradesh', 'Arunachal Pradesh', 'Assam', 'Bihar', 'Chandigarh',
  'Chhattisgarh', 'Dadra and Nagar Haveli and Daman and Diu', 'Delhi', 'Goa', 'Gujarat', 'Haryana',
  'Himachal Pradesh', 'Jammu and Kashmir', 'Jharkhand', 'Karnataka', 'Kerala', 'Ladakh', 'Lakshadweep',
  'Madhya Pradesh', 'Maharashtra', 'Manipur', 'Meghalaya', 'Mizoram', 'Nagaland', 'Odisha', 'Puducherry',
  'Punjab', 'Rajasthan', 'Sikkim', 'Tamil Nadu', 'Telangana', 'Tripura', 'Uttar Pradesh', 'Uttarakhand',
  'West Bengal',
]

export const UPLOAD_DEFAULTS = {
  max_files: 5, max_image_mb: 10, max_video_mb: 50, max_pdf_mb: 10, max_total_mb: 80,
  accept: '.jpg,.jpeg,.png,.webp,.mp4,.m4v,.mov,.3gp,.webm,.pdf',
}
