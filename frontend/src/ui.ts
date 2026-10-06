import type { User } from './auth'
export const translate = (user: User) => (en: string, hi: string) => user.preferred_language === 'en' ? en : hi
export function statusLabel(status: string | null, hi: boolean) {
  const labels: Record<string, [string, string]> = {
    answered:['Answered','उत्तर मिला'], partial:['Partial answer','आंशिक उत्तर'],
    clarification_required:['Clarification needed','प्रश्न स्पष्ट करें'], insufficient_evidence:['Insufficient evidence','पर्याप्त साक्ष्य नहीं'],
    needs_clarification:['Clarification needed','प्रश्न स्पष्ट करें'], abstained:['Insufficient evidence','पर्याप्त साक्ष्य नहीं'],
    queued:['Waiting','प्रतीक्षा में'], processing:['Checking evidence','साक्ष्य की जाँच'],
    error:['Unable to answer','उत्तर नहीं बन पाया'], cancelled:['Cancelled','रद्द'], done:['Completed','पूरा हुआ'],
  }
  return labels[status || '']?.[hi ? 1 : 0] || status || (hi ? 'अभी उत्तर नहीं' : 'No answer yet')
}
