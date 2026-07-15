// Minimal i18n for the rep app — Hindi / Bengali / English.
//
// Deliberately dependency-free (a few hundred bytes instead of vue-i18n): this bundle
// already fought CJS-only deps once, and the need here is one lookup and one switch.
//
// The KEY IS THE ENGLISH STRING. Anything not yet translated renders in English rather
// than a missing-key placeholder, so partial coverage degrades quietly instead of
// showing "nav.home" to a rep standing in front of a dealer.
//
// Reactivity: t() reads locale.value during render, so switching language re-renders
// every component that used it — no reload.
import { ref } from "vue"

const KEY = "triam_lang"

export const LANGS = [
	{ code: "en", label: "English" },
	{ code: "hi", label: "हिन्दी" },
	{ code: "bn", label: "বাংলা" },
]

function initial() {
	try {
		const saved = localStorage.getItem(KEY)
		if (saved) return saved
		// Fall back to the phone's language: most reps never open settings.
		const nav = (navigator.language || "en").toLowerCase()
		if (nav.startsWith("hi")) return "hi"
		if (nav.startsWith("bn")) return "bn"
	} catch (e) {
		/* private mode */
	}
	return "en"
}

export const locale = ref(initial())

export function setLocale(code) {
	locale.value = code
	try {
		localStorage.setItem(KEY, code)
	} catch (e) {
		/* ignore */
	}
}

const hi = {
	// Navigation
	Home: "होम",
	Visits: "विज़िट",
	Start: "शुरू",
	Dealers: "डीलर",
	More: "और",
	// Home / dashboard
	"Today's beat": "आज का बीट",
	"Start visit": "विज़िट शुरू करें",
	Visited: "विज़िट हुआ",
	Planned: "योजना",
	Target: "टारगेट",
	Achievement: "उपलब्धि",
	Sales: "बिक्री",
	Orders: "ऑर्डर",
	// Visit flow
	"New visit": "नई विज़िट",
	"Check in": "चेक इन",
	"Check out": "चेक आउट",
	Purpose: "उद्देश्य",
	Notes: "नोट्स",
	Outcome: "नतीजा",
	Photos: "फोटो",
	"Add photo": "फोटो जोड़ें",
	Competitor: "प्रतिस्पर्धी",
	// Attendance
	Attendance: "हाजिरी",
	"Mark attendance": "हाजिरी लगाएं",
	// Money
	Conveyance: "यात्रा भत्ता",
	"Collect payment": "पेमेंट लें",
	Collect: "वसूली",
	Collections: "वसूली",
	"Amount collected": "प्राप्त राशि",
	Mode: "माध्यम",
	Cash: "नकद",
	Cheque: "चेक",
	Outstanding: "बकाया",
	Overdue: "अतिदेय",
	"Expense claims": "खर्च दावा",
	Expense: "खर्च",
	Salary: "वेतन",
	Leave: "छुट्टी",
	// Customer 360
	"Business done": "कुल कारोबार",
	"Last visit": "पिछली विज़िट",
	"Last order": "पिछला ऑर्डर",
	"Buys most": "सबसे ज्यादा खरीदता है",
	"Recent orders": "हाल के ऑर्डर",
	"Visit history": "विज़िट इतिहास",
	Navigate: "रास्ता",
	Call: "कॉल",
	"At risk": "जोखिम में",
	"No location": "लोकेशन नहीं",
	"Pin this shop": "दुकान पिन करें",
	// Common
	Save: "सेव करें",
	Cancel: "रद्द करें",
	Submit: "जमा करें",
	Search: "खोजें",
	Today: "आज",
	Yesterday: "कल",
	Never: "कभी नहीं",
	Remarks: "टिप्पणी",
	Optional: "वैकल्पिक",
	Language: "भाषा",
	Logout: "लॉग आउट",
	Schemes: "स्कीम",
	Targets: "टारगेट",
	Route: "रूट",
	Team: "टीम",
	Approvals: "अनुमोदन",
	Holidays: "छुट्टियाँ",
	// More menu
	"Beat plan": "बीट प्लान",
	"My targets": "मेरे टारगेट",
	"Salary slips": "सैलरी स्लिप",
	"My KRA scorecard": "मेरा KRA स्कोरकार्ड",
	"Activity timeline": "गतिविधि टाइमलाइन",
	"Smart insights": "स्मार्ट जानकारी",
	"Active schemes": "चालू स्कीम",
	Notifications: "सूचनाएं",
	Analytics: "एनालिटिक्स",
	"Team activity": "टीम गतिविधि",
	"Team live map": "टीम लाइव मैप",
	"My workplace": "मेरा कार्यस्थल",
	Security: "सुरक्षा",
	Manager: "मैनेजर",
	"Sign out": "साइन आउट",
}

const bn = {
	// Navigation
	Home: "হোম",
	Visits: "ভিজিট",
	Start: "শুরু",
	Dealers: "ডিলার",
	More: "আরও",
	// Home / dashboard
	"Today's beat": "আজকের বিট",
	"Start visit": "ভিজিট শুরু করুন",
	Visited: "ভিজিট হয়েছে",
	Planned: "পরিকল্পিত",
	Target: "টার্গেট",
	Achievement: "অর্জন",
	Sales: "বিক্রয়",
	Orders: "অর্ডার",
	// Visit flow
	"New visit": "নতুন ভিজিট",
	"Check in": "চেক ইন",
	"Check out": "চেক আউট",
	Purpose: "উদ্দেশ্য",
	Notes: "নোট",
	Outcome: "ফলাফল",
	Photos: "ছবি",
	"Add photo": "ছবি যোগ করুন",
	Competitor: "প্রতিযোগী",
	// Attendance
	Attendance: "হাজিরা",
	"Mark attendance": "হাজিরা দিন",
	// Money
	Conveyance: "যাতায়াত ভাতা",
	"Collect payment": "পেমেন্ট নিন",
	Collect: "আদায়",
	Collections: "আদায়",
	"Amount collected": "প্রাপ্ত টাকা",
	Mode: "মাধ্যম",
	Cash: "নগদ",
	Cheque: "চেক",
	Outstanding: "বকেয়া",
	Overdue: "মেয়াদোত্তীর্ণ",
	"Expense claims": "খরচের দাবি",
	Expense: "খরচ",
	Salary: "বেতন",
	Leave: "ছুটি",
	// Customer 360
	"Business done": "মোট ব্যবসা",
	"Last visit": "শেষ ভিজিট",
	"Last order": "শেষ অর্ডার",
	"Buys most": "সবচেয়ে বেশি কেনে",
	"Recent orders": "সাম্প্রতিক অর্ডার",
	"Visit history": "ভিজিট ইতিহাস",
	Navigate: "পথ",
	Call: "কল",
	"At risk": "ঝুঁকিতে",
	"No location": "লোকেশন নেই",
	"Pin this shop": "দোকান পিন করুন",
	// Common
	Save: "সেভ করুন",
	Cancel: "বাতিল",
	Submit: "জমা দিন",
	Search: "খুঁজুন",
	Today: "আজ",
	Yesterday: "গতকাল",
	Never: "কখনও নয়",
	Remarks: "মন্তব্য",
	Optional: "ঐচ্ছিক",
	Language: "ভাষা",
	Logout: "লগ আউট",
	Schemes: "স্কিম",
	Targets: "টার্গেট",
	Route: "রুট",
	Team: "টিম",
	Approvals: "অনুমোদন",
	Holidays: "ছুটির দিন",
	// More menu
	"Beat plan": "বিট প্ল্যান",
	"My targets": "আমার টার্গেট",
	"Salary slips": "বেতন স্লিপ",
	"My KRA scorecard": "আমার KRA স্কোরকার্ড",
	"Activity timeline": "কার্যকলাপ টাইমলাইন",
	"Smart insights": "স্মার্ট তথ্য",
	"Active schemes": "চালু স্কিম",
	Notifications: "বিজ্ঞপ্তি",
	Analytics: "অ্যানালিটিক্স",
	"Team activity": "টিম কার্যকলাপ",
	"Team live map": "টিম লাইভ ম্যাপ",
	"My workplace": "আমার কর্মস্থল",
	Security: "নিরাপত্তা",
	Manager: "ম্যানেজার",
	"Sign out": "সাইন আউট",
}

const DICT = { hi, bn }

/** Translate an English string. Unknown strings pass through unchanged. */
export function t(s) {
	if (locale.value === "en") return s
	return DICT[locale.value]?.[s] ?? s
}
