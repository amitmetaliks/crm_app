// Minimal i18n for the rep app — Hindi / Bengali / English.
//
// Deliberately dependency-free (a few KB instead of vue-i18n): this bundle already
// fought CJS-only deps once, and the need here is one lookup and one switch.
//
// THE KEY IS THE ENGLISH STRING. Anything not yet translated renders in English rather
// than a missing-key placeholder, so partial coverage degrades quietly instead of
// showing "nav.home" to a rep standing in front of a dealer.
//
// Reactivity: t() reads locale.value during render, so switching language re-renders
// every component that used it — no reload.
//
// Register-transfer note: Hinglish/Banglish is deliberate where the trade uses English
// terms daily (ऑर्डर, टारगेट, स्टॉक, KRA, MT). Translating those "properly" would read
// as officialese to a rep and slow him down.
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
	// ---- Navigation / shell ----
	Home: "होम",
	Visits: "विज़िट",
	Start: "शुरू",
	Dealers: "डीलर",
	More: "और",
	Back: "वापस",
	Language: "भाषा",
	"Sign out": "साइन आउट",
	"My workplace": "मेरा कार्यस्थल",
	Security: "सुरक्षा",
	Manager: "मैनेजर",
	"Field Sales": "फील्ड सेल्स",

	// ---- Login ----
	"Sign in": "साइन इन",
	"Use your company login": "अपना कंपनी लॉगिन इस्तेमाल करें",
	"Email / Username": "ईमेल / यूज़रनेम",
	Password: "पासवर्ड",

	// ---- Dashboard ----
	"Start a Visit": "विज़िट शुरू करें",
	Today: "आज",
	Productive: "उत्पादक",
	"Zero order": "बिना ऑर्डर",
	Strike: "स्ट्राइक",
	"Orders today": "आज के ऑर्डर",
	"Order value": "ऑर्डर वैल्यू",
	"Total qty": "कुल मात्रा",
	"New retailers (mo)": "नए रिटेलर (महीना)",
	"Sales target (month)": "सेल्स टारगेट (महीना)",
	Expenses: "खर्च",
	KRA: "KRA",
	Timeline: "टाइमलाइन",
	Collect: "वसूली",

	// ---- New visit ----
	"Who are you visiting?": "आप किससे मिल रहे हैं?",
	Change: "बदलें",
	"No matches": "कुछ नहीं मिला",
	"Use this": "इसे चुनें",
	Cancel: "रद्द करें",
	Purpose: "उद्देश्य",
	Photos: "फोटो",
	Add: "जोड़ें",
	"Orders / Inquiries": "ऑर्डर / पूछताछ",
	Inquiry: "पूछताछ",
	"Firm Order": "पक्का ऑर्डर",
	Grade: "ग्रेड",
	"No orders/inquiries added.": "कोई ऑर्डर/पूछताछ नहीं जोड़ी गई।",
	"Competitor info": "प्रतिस्पर्धी जानकारी",
	Stock: "स्टॉक",
	"In Stock": "स्टॉक में",
	"Low Stock": "कम स्टॉक",
	"Out of Stock": "स्टॉक खत्म",
	"No competitor info added.": "प्रतिस्पर्धी जानकारी नहीं जोड़ी गई।",
	Notes: "नोट्स",
	Positive: "सकारात्मक",
	Neutral: "सामान्य",
	Negative: "नकारात्मक",
	"Order Received": "ऑर्डर मिला",
	"No Interest": "रुचि नहीं",
	Save: "सेव करें",
	"Check in": "चेक इन",
	"Check out": "चेक आउट",
	"Search dealer / customer / lead…": "डीलर / ग्राहक / लीड खोजें…",
	"Prospect / shop name": "संभावित ग्राहक / दुकान का नाम",
	"Contact name": "संपर्क का नाम",
	Phone: "फोन",
	"Qty (MT)": "मात्रा (MT)",
	"Rate/MT": "रेट/MT",
	"Value ₹": "वैल्यू ₹",
	Brand: "ब्रांड",
	"Price/MT": "कीमत/MT",
	"What happened on this visit?": "इस विज़िट में क्या हुआ?",
	"Next action": "अगला कदम",

	// ---- Visits / visit detail ----
	"Show whole team": "पूरी टीम दिखाएं",
	"No visits found": "कोई विज़िट नहीं मिली",
	"Check-in": "चेक-इन",
	"Check-out": "चेक-आउट",
	"View on map": "मैप पर देखें",
	"Book Sales Order": "सेल्स ऑर्डर बुक करें",
	Schemes: "स्कीम",
	"Share with dealer (WhatsApp)": "डीलर को भेजें (WhatsApp)",
	"Check out now": "अभी चेक आउट करें",
	"Search catalog item…": "आइटम खोजें…",
	Qty: "मात्रा",
	Rate: "रेट",
	"Visit not found": "विज़िट नहीं मिली",

	// ---- Customers / 360 ----
	"Dealers & Customers": "डीलर और ग्राहक",
	"Search dealers, leads…": "डीलर, लीड खोजें…",
	"Try another name.": "दूसरा नाम आज़माएं।",
	"At risk": "जोखिम में",
	Call: "कॉल",
	WhatsApp: "WhatsApp",
	Navigate: "रास्ता",
	"No location": "लोकेशन नहीं",
	"No location on record. Stand at the shop and tap": "लोकेशन दर्ज नहीं है। दुकान पर खड़े होकर दबाएं",
	"Pin this shop": "दुकान पिन करें",
	"Re-pin shop": "दुकान फिर पिन करें",
	Outstanding: "बकाया",
	"Business done": "कुल कारोबार",
	"Last visit": "पिछली विज़िट",
	"Last order": "पिछला ऑर्डर",
	"Start visit": "विज़िट शुरू करें",
	"Buys most": "सबसे ज्यादा खरीदता है",
	"Recent orders": "हाल के ऑर्डर",
	"Visit history": "विज़िट इतिहास",
	"No visits yet": "अभी कोई विज़िट नहीं",
	"Customer not found": "ग्राहक नहीं मिला",

	// ---- Attendance ----
	Attendance: "हाजिरी",
	Out: "बाहर",
	"Today's punches": "आज की हाजिरी",
	"No punches yet today": "आज अभी कोई हाजिरी नहीं",

	// ---- Conveyance ----
	Conveyance: "यात्रा भत्ता",
	"Conveyance already claimed": "यात्रा भत्ता पहले ही लिया जा चुका है",
	"View my claims": "मेरे दावे देखें",
	"Distance recorded today": "आज दर्ज दूरी",
	"Actual distance (km)": "वास्तविक दूरी (किमी)",
	Reason: "कारण",
	"Attach proof (optional)": "सबूत लगाएं (वैकल्पिक)",
	Claiming: "दावा",
	"No travel rate set": "यात्रा दर तय नहीं है",
	"Ask HR to set 'Travel Allowance Per Km' on your Sales Person record, then this will calculate automatically.":
		"HR से कहें कि आपके Sales Person रिकॉर्ड में 'Travel Allowance Per Km' भरें, फिर यह अपने आप गिना जाएगा।",
	"No unpaid invoices found for your dealers. To collect money anyway, open the dealer and tap Collect.":
		"आपके डीलरों का कोई बकाया बिल नहीं मिला। फिर भी पैसा लेना हो तो डीलर खोलकर 'वसूली' दबाएं।",

	// ---- Collect ----
	"Collect payment": "पेमेंट लें",
	"Send receipt on WhatsApp": "WhatsApp पर रसीद भेजें",
	Done: "हो गया",
	"Amount collected": "प्राप्त राशि",
	Mode: "माध्यम",
	Cash: "नकद",
	Cheque: "चेक",
	Remarks: "टिप्पणी",
	"Photo (cash / cheque / slip)": "फोटो (नकद / चेक / पर्ची)",
	Optional: "वैकल्पिक",

	// ---- Expense / leave / salary ----
	"Expense Claims": "खर्च दावा",
	"Expense claims": "खर्च दावा",
	"New claim": "नया दावा",
	Submit: "जमा करें",
	"Amount ₹": "राशि ₹",
	"Description (e.g. fuel Kolkata-Durgapur)": "विवरण (जैसे ईंधन कोलकाता-दुर्गापुर)",
	"No claims yet": "अभी कोई दावा नहीं",
	"Submit your first expense claim.": "अपना पहला खर्च दावा जमा करें।",
	Leave: "छुट्टी",
	Balance: "बाकी",
	"Apply for leave": "छुट्टी के लिए आवेदन",
	Apply: "आवेदन करें",
	"Salary Slips": "सैलरी स्लिप",
	"Salary slips": "सैलरी स्लिप",
	"Net Pay": "शुद्ध वेतन",
	"No salary slips": "कोई सैलरी स्लिप नहीं",
	"Your payslips will appear here.": "आपकी सैलरी स्लिप यहां दिखेंगी।",
	Holidays: "छुट्टियाँ",

	// ---- Beat ----
	"Today's Beat": "आज का बीट",
	"Beat plan": "बीट प्लान",
	Visit: "विज़िट",
	Maps: "मैप",
	"Edit beat": "बीट बदलें",
	"Plan beat": "बीट बनाएं",
	Primary: "प्राइमरी",
	Secondary: "सेकंडरी",
	"Save beat": "बीट सेव करें",
	"No beat planned": "कोई बीट नहीं बना",
	"Plan the dealers you'll visit today.": "आज जिन डीलरों से मिलना है उन्हें चुनें।",
	"Beat title (e.g. North zone)": "बीट का नाम (जैसे उत्तर क्षेत्र)",
	"Territory (e.g. West Bengal)": "क्षेत्र (जैसे पश्चिम बंगाल)",
	"Add dealer…": "डीलर जोड़ें…",

	// ---- Targets ----
	"My Targets": "मेरे टारगेट",
	"My targets": "मेरे टारगेट",
	"Target vs achievement": "टारगेट बनाम उपलब्धि",
	Value: "वैल्यू",
	Quantity: "मात्रा",
	"No targets set": "कोई टारगेट तय नहीं",
	"Your manager hasn't assigned targets yet.": "आपके मैनेजर ने अभी टारगेट नहीं दिया है।",

	// ---- Collections ----
	Collections: "वसूली",
	Overdue: "अतिदेय",
	Remind: "याद दिलाएं",
	"Nothing outstanding": "कोई बकाया नहीं",

	// ---- Route / schemes / timeline / insights ----
	"My Route": "मेरा रूट",
	"My route & distance": "मेरा रूट और दूरी",
	"Open route in Google Maps": "Google Maps में रूट खोलें",
	"No visits this day": "इस दिन कोई विज़िट नहीं",
	"Active Schemes": "चालू स्कीम",
	"Active schemes": "चालू स्कीम",
	"No active schemes": "कोई चालू स्कीम नहीं",
	"No current offers/discounts are running.": "अभी कोई ऑफर/छूट नहीं चल रही।",
	"Activity Timeline": "गतिविधि टाइमलाइन",
	"Activity timeline": "गतिविधि टाइमलाइन",
	"No activity": "कोई गतिविधि नहीं",
	"No activity recorded for this date.": "इस तारीख की कोई गतिविधि दर्ज नहीं।",
	"Smart Insights": "स्मार्ट जानकारी",
	"Smart insights": "स्मार्ट जानकारी",
	Mine: "मेरा",
	Team: "टीम",
	"Sales forecast (next month)": "बिक्री अनुमान (अगला महीना)",
	"No sales history yet.": "अभी बिक्री का इतिहास नहीं।",
	"Based on the average of recent months' booked orders.": "पिछले महीनों के औसत ऑर्डर के आधार पर।",
	"All dealers active": "सभी डीलर सक्रिय",
	"No dealers are slipping — nice work.": "कोई डीलर छूट नहीं रहा — बढ़िया काम।",
	"My KRA scorecard": "मेरा KRA स्कोरकार्ड",

	// ---- Notifications ----
	Notifications: "सूचनाएं",
	"Push notifications": "पुश सूचनाएं",
	"Send a test notification": "टेस्ट सूचना भेजें",

	// ---- Leads ----
	"Leads & Deals": "लीड और डील",
	Leads: "लीड",
	Deals: "डील",
	"New lead": "नई लीड",
	"Name / Shop / Firm *": "नाम / दुकान / फर्म *",
	Mobile: "मोबाइल",
	Email: "ईमेल",
	"Area / Territory": "इलाका / क्षेत्र",

	// ---- Lock ----
	"App locked": "ऐप लॉक है",
	"Enter your PIN to continue": "जारी रखने के लिए PIN डालें",
	"Wrong PIN, try again": "गलत PIN, फिर कोशिश करें",

	// ---- Manager ----
	Approvals: "अनुमोदन",
	"GPS recorded": "GPS दर्ज",
	"Rep claims": "रेप का दावा",
	Reject: "अस्वीकार",
	Approve: "स्वीकार",
	"Leave requests": "छुट्टी के आवेदन",
	"Visits to verify": "जांचने वाली विज़िट",
	Verify: "जांचें",
	"All clear": "सब ठीक",
	"Nothing waiting for your approval.": "आपकी मंज़ूरी के लिए कुछ नहीं है।",
	Analytics: "एनालिटिक्स",
	"Order conversion": "ऑर्डर रूपांतरण",
	"Beat adherence": "बीट पालन",
	"Present today": "आज उपस्थित",
	"Visits completed": "पूरी हुई विज़िट",
	Receivables: "प्राप्य",
	"Pending approval": "मंज़ूरी बाकी",
	"Top products (by order value, this month)": "टॉप उत्पाद (ऑर्डर वैल्यू, इस महीने)",
	"Managers only": "सिर्फ मैनेजर",
	"Team Activity": "टीम गतिविधि",
	"Team activity": "टीम गतिविधि",
	"Team live map": "टीम लाइव मैप",
	"Today's coverage": "आज की कवरेज",
	"Recent team visits": "हाल की टीम विज़िट",
	"This view is for sales managers.": "यह स्क्रीन सेल्स मैनेजर के लिए है।",
	"No visits yet today": "आज अभी कोई विज़िट नहीं",
	Refresh: "रिफ्रेश",
	Map: "मैप",
	"No reps reporting yet": "अभी कोई रेप रिपोर्ट नहीं कर रहा",
	"Locations appear once reps open the app today.": "रेप के ऐप खोलते ही लोकेशन दिखेंगी।",

	// ---- Common ----
	Search: "खोजें",
	Yesterday: "कल",
	Never: "कभी नहीं",
	Target: "टारगेट",
	Achievement: "उपलब्धि",
	Sales: "बिक्री",
	Orders: "ऑर्डर",
	Planned: "योजना",
	Visited: "विज़िट हुआ",
	Route: "रूट",
	Targets: "टारगेट",
	Expense: "खर्च",
	Salary: "वेतन",
}

const bn = {
	// ---- Navigation / shell ----
	Home: "হোম",
	Visits: "ভিজিট",
	Start: "শুরু",
	Dealers: "ডিলার",
	More: "আরও",
	Back: "পিছনে",
	Language: "ভাষা",
	"Sign out": "সাইন আউট",
	"My workplace": "আমার কর্মস্থল",
	Security: "নিরাপত্তা",
	Manager: "ম্যানেজার",
	"Field Sales": "ফিল্ড সেলস",

	// ---- Login ----
	"Sign in": "সাইন ইন",
	"Use your company login": "আপনার কোম্পানির লগইন ব্যবহার করুন",
	"Email / Username": "ইমেল / ইউজারনেম",
	Password: "পাসওয়ার্ড",

	// ---- Dashboard ----
	"Start a Visit": "ভিজিট শুরু করুন",
	Today: "আজ",
	Productive: "উৎপাদনশীল",
	"Zero order": "অর্ডার ছাড়া",
	Strike: "স্ট্রাইক",
	"Orders today": "আজকের অর্ডার",
	"Order value": "অর্ডার মূল্য",
	"Total qty": "মোট পরিমাণ",
	"New retailers (mo)": "নতুন রিটেলার (মাস)",
	"Sales target (month)": "সেলস টার্গেট (মাস)",
	Expenses: "খরচ",
	KRA: "KRA",
	Timeline: "টাইমলাইন",
	Collect: "আদায়",

	// ---- New visit ----
	"Who are you visiting?": "আপনি কার কাছে যাচ্ছেন?",
	Change: "পরিবর্তন",
	"No matches": "কিছু পাওয়া যায়নি",
	"Use this": "এটি বেছে নিন",
	Cancel: "বাতিল",
	Purpose: "উদ্দেশ্য",
	Photos: "ছবি",
	Add: "যোগ করুন",
	"Orders / Inquiries": "অর্ডার / অনুসন্ধান",
	Inquiry: "অনুসন্ধান",
	"Firm Order": "পাকা অর্ডার",
	Grade: "গ্রেড",
	"No orders/inquiries added.": "কোনো অর্ডার/অনুসন্ধান যোগ করা হয়নি।",
	"Competitor info": "প্রতিযোগীর তথ্য",
	Stock: "স্টক",
	"In Stock": "স্টকে আছে",
	"Low Stock": "কম স্টক",
	"Out of Stock": "স্টক শেষ",
	"No competitor info added.": "প্রতিযোগীর তথ্য যোগ করা হয়নি।",
	Notes: "নোট",
	Positive: "ইতিবাচক",
	Neutral: "সাধারণ",
	Negative: "নেতিবাচক",
	"Order Received": "অর্ডার পাওয়া গেছে",
	"No Interest": "আগ্রহ নেই",
	Save: "সেভ করুন",
	"Check in": "চেক ইন",
	"Check out": "চেক আউট",
	"Search dealer / customer / lead…": "ডিলার / গ্রাহক / লিড খুঁজুন…",
	"Prospect / shop name": "সম্ভাব্য গ্রাহক / দোকানের নাম",
	"Contact name": "যোগাযোগের নাম",
	Phone: "ফোন",
	"Qty (MT)": "পরিমাণ (MT)",
	"Rate/MT": "রেট/MT",
	"Value ₹": "মূল্য ₹",
	Brand: "ব্র্যান্ড",
	"Price/MT": "দাম/MT",
	"What happened on this visit?": "এই ভিজিটে কী হয়েছে?",
	"Next action": "পরবর্তী পদক্ষেপ",

	// ---- Visits / visit detail ----
	"Show whole team": "পুরো টিম দেখান",
	"No visits found": "কোনো ভিজিট পাওয়া যায়নি",
	"Check-in": "চেক-ইন",
	"Check-out": "চেক-আউট",
	"View on map": "ম্যাপে দেখুন",
	"Book Sales Order": "সেলস অর্ডার বুক করুন",
	Schemes: "স্কিম",
	"Share with dealer (WhatsApp)": "ডিলারকে পাঠান (WhatsApp)",
	"Check out now": "এখনই চেক আউট করুন",
	"Search catalog item…": "আইটেম খুঁজুন…",
	Qty: "পরিমাণ",
	Rate: "রেট",
	"Visit not found": "ভিজিট পাওয়া যায়নি",

	// ---- Customers / 360 ----
	"Dealers & Customers": "ডিলার ও গ্রাহক",
	"Search dealers, leads…": "ডিলার, লিড খুঁজুন…",
	"Try another name.": "অন্য নাম চেষ্টা করুন।",
	"At risk": "ঝুঁকিতে",
	Call: "কল",
	WhatsApp: "WhatsApp",
	Navigate: "পথ",
	"No location": "লোকেশন নেই",
	"No location on record. Stand at the shop and tap": "লোকেশন নথিভুক্ত নেই। দোকানে দাঁড়িয়ে চাপুন",
	"Pin this shop": "দোকান পিন করুন",
	"Re-pin shop": "দোকান আবার পিন করুন",
	Outstanding: "বকেয়া",
	"Business done": "মোট ব্যবসা",
	"Last visit": "শেষ ভিজিট",
	"Last order": "শেষ অর্ডার",
	"Start visit": "ভিজিট শুরু করুন",
	"Buys most": "সবচেয়ে বেশি কেনে",
	"Recent orders": "সাম্প্রতিক অর্ডার",
	"Visit history": "ভিজিট ইতিহাস",
	"No visits yet": "এখনও কোনো ভিজিট নেই",
	"Customer not found": "গ্রাহক পাওয়া যায়নি",

	// ---- Attendance ----
	Attendance: "হাজিরা",
	Out: "বাইরে",
	"Today's punches": "আজকের হাজিরা",
	"No punches yet today": "আজ এখনও হাজিরা নেই",

	// ---- Conveyance ----
	Conveyance: "যাতায়াত ভাতা",
	"Conveyance already claimed": "যাতায়াত ভাতা ইতিমধ্যে নেওয়া হয়েছে",
	"View my claims": "আমার দাবি দেখুন",
	"Distance recorded today": "আজ রেকর্ড করা দূরত্ব",
	"Actual distance (km)": "প্রকৃত দূরত্ব (কিমি)",
	Reason: "কারণ",
	"Attach proof (optional)": "প্রমাণ যুক্ত করুন (ঐচ্ছিক)",
	Claiming: "দাবি",
	"No travel rate set": "যাতায়াত রেট নির্ধারিত নেই",
	"Ask HR to set 'Travel Allowance Per Km' on your Sales Person record, then this will calculate automatically.":
		"HR-কে বলুন আপনার Sales Person রেকর্ডে 'Travel Allowance Per Km' বসাতে, তারপর এটি নিজে থেকেই হিসাব হবে।",
	"No unpaid invoices found for your dealers. To collect money anyway, open the dealer and tap Collect.":
		"আপনার ডিলারদের কোনো বকেয়া বিল পাওয়া যায়নি। তবুও টাকা নিতে হলে ডিলার খুলে 'আদায়' চাপুন।",

	// ---- Collect ----
	"Collect payment": "পেমেন্ট নিন",
	"Send receipt on WhatsApp": "WhatsApp-এ রসিদ পাঠান",
	Done: "সম্পন্ন",
	"Amount collected": "প্রাপ্ত টাকা",
	Mode: "মাধ্যম",
	Cash: "নগদ",
	Cheque: "চেক",
	Remarks: "মন্তব্য",
	"Photo (cash / cheque / slip)": "ছবি (নগদ / চেক / স্লিপ)",
	Optional: "ঐচ্ছিক",

	// ---- Expense / leave / salary ----
	"Expense Claims": "খরচের দাবি",
	"Expense claims": "খরচের দাবি",
	"New claim": "নতুন দাবি",
	Submit: "জমা দিন",
	"Amount ₹": "টাকা ₹",
	"Description (e.g. fuel Kolkata-Durgapur)": "বিবরণ (যেমন জ্বালানি কলকাতা-দুর্গাপুর)",
	"No claims yet": "এখনও কোনো দাবি নেই",
	"Submit your first expense claim.": "আপনার প্রথম খরচের দাবি জমা দিন।",
	Leave: "ছুটি",
	Balance: "বাকি",
	"Apply for leave": "ছুটির আবেদন",
	Apply: "আবেদন করুন",
	"Salary Slips": "বেতন স্লিপ",
	"Salary slips": "বেতন স্লিপ",
	"Net Pay": "নিট বেতন",
	"No salary slips": "কোনো বেতন স্লিপ নেই",
	"Your payslips will appear here.": "আপনার বেতন স্লিপ এখানে দেখাবে।",
	Holidays: "ছুটির দিন",

	// ---- Beat ----
	"Today's Beat": "আজকের বিট",
	"Beat plan": "বিট প্ল্যান",
	Visit: "ভিজিট",
	Maps: "ম্যাপ",
	"Edit beat": "বিট সম্পাদনা",
	"Plan beat": "বিট তৈরি করুন",
	Primary: "প্রাইমারি",
	Secondary: "সেকেন্ডারি",
	"Save beat": "বিট সেভ করুন",
	"No beat planned": "কোনো বিট তৈরি হয়নি",
	"Plan the dealers you'll visit today.": "আজ যে ডিলারদের কাছে যাবেন তাদের বাছুন।",
	"Beat title (e.g. North zone)": "বিটের নাম (যেমন উত্তর অঞ্চল)",
	"Territory (e.g. West Bengal)": "অঞ্চল (যেমন পশ্চিমবঙ্গ)",
	"Add dealer…": "ডিলার যোগ করুন…",

	// ---- Targets ----
	"My Targets": "আমার টার্গেট",
	"My targets": "আমার টার্গেট",
	"Target vs achievement": "টার্গেট বনাম অর্জন",
	Value: "মূল্য",
	Quantity: "পরিমাণ",
	"No targets set": "কোনো টার্গেট নেই",
	"Your manager hasn't assigned targets yet.": "আপনার ম্যানেজার এখনও টার্গেট দেননি।",

	// ---- Collections ----
	Collections: "আদায়",
	Overdue: "মেয়াদোত্তীর্ণ",
	Remind: "মনে করান",
	"Nothing outstanding": "কোনো বকেয়া নেই",

	// ---- Route / schemes / timeline / insights ----
	"My Route": "আমার রুট",
	"My route & distance": "আমার রুট ও দূরত্ব",
	"Open route in Google Maps": "Google Maps-এ রুট খুলুন",
	"No visits this day": "এই দিনে কোনো ভিজিট নেই",
	"Active Schemes": "চালু স্কিম",
	"Active schemes": "চালু স্কিম",
	"No active schemes": "কোনো চালু স্কিম নেই",
	"No current offers/discounts are running.": "এখন কোনো অফার/ছাড় চলছে না।",
	"Activity Timeline": "কার্যকলাপ টাইমলাইন",
	"Activity timeline": "কার্যকলাপ টাইমলাইন",
	"No activity": "কোনো কার্যকলাপ নেই",
	"No activity recorded for this date.": "এই তারিখে কোনো কার্যকলাপ নেই।",
	"Smart Insights": "স্মার্ট তথ্য",
	"Smart insights": "স্মার্ট তথ্য",
	Mine: "আমার",
	Team: "টিম",
	"Sales forecast (next month)": "বিক্রয় পূর্বাভাস (পরের মাস)",
	"No sales history yet.": "এখনও বিক্রয়ের ইতিহাস নেই।",
	"Based on the average of recent months' booked orders.": "সাম্প্রতিক মাসগুলির গড় অর্ডারের ভিত্তিতে।",
	"All dealers active": "সব ডিলার সক্রিয়",
	"No dealers are slipping — nice work.": "কোনো ডিলার হারাচ্ছে না — দারুণ কাজ।",
	"My KRA scorecard": "আমার KRA স্কোরকার্ড",

	// ---- Notifications ----
	Notifications: "বিজ্ঞপ্তি",
	"Push notifications": "পুশ বিজ্ঞপ্তি",
	"Send a test notification": "টেস্ট বিজ্ঞপ্তি পাঠান",

	// ---- Leads ----
	"Leads & Deals": "লিড ও ডিল",
	Leads: "লিড",
	Deals: "ডিল",
	"New lead": "নতুন লিড",
	"Name / Shop / Firm *": "নাম / দোকান / ফার্ম *",
	Mobile: "মোবাইল",
	Email: "ইমেল",
	"Area / Territory": "এলাকা / অঞ্চল",

	// ---- Lock ----
	"App locked": "অ্যাপ লক করা",
	"Enter your PIN to continue": "চালিয়ে যেতে PIN দিন",
	"Wrong PIN, try again": "ভুল PIN, আবার চেষ্টা করুন",

	// ---- Manager ----
	Approvals: "অনুমোদন",
	"GPS recorded": "GPS রেকর্ড",
	"Rep claims": "রেপের দাবি",
	Reject: "প্রত্যাখ্যান",
	Approve: "অনুমোদন",
	"Leave requests": "ছুটির আবেদন",
	"Visits to verify": "যাচাই করার ভিজিট",
	Verify: "যাচাই করুন",
	"All clear": "সব ঠিক",
	"Nothing waiting for your approval.": "আপনার অনুমোদনের জন্য কিছু নেই।",
	Analytics: "অ্যানালিটিক্স",
	"Order conversion": "অর্ডার রূপান্তর",
	"Beat adherence": "বিট পালন",
	"Present today": "আজ উপস্থিত",
	"Visits completed": "সম্পন্ন ভিজিট",
	Receivables: "প্রাপ্য",
	"Pending approval": "অনুমোদন বাকি",
	"Top products (by order value, this month)": "শীর্ষ পণ্য (অর্ডার মূল্য, এই মাস)",
	"Managers only": "শুধু ম্যানেজার",
	"Team Activity": "টিম কার্যকলাপ",
	"Team activity": "টিম কার্যকলাপ",
	"Team live map": "টিম লাইভ ম্যাপ",
	"Today's coverage": "আজকের কভারেজ",
	"Recent team visits": "সাম্প্রতিক টিম ভিজিট",
	"This view is for sales managers.": "এই স্ক্রিন সেলস ম্যানেজারদের জন্য।",
	"No visits yet today": "আজ এখনও কোনো ভিজিট নেই",
	Refresh: "রিফ্রেশ",
	Map: "ম্যাপ",
	"No reps reporting yet": "এখনও কোনো রেপ রিপোর্ট করছে না",
	"Locations appear once reps open the app today.": "রেপরা অ্যাপ খুললেই লোকেশন দেখাবে।",

	// ---- Common ----
	Search: "খুঁজুন",
	Yesterday: "গতকাল",
	Never: "কখনও নয়",
	Target: "টার্গেট",
	Achievement: "অর্জন",
	Sales: "বিক্রয়",
	Orders: "অর্ডার",
	Planned: "পরিকল্পিত",
	Visited: "ভিজিট হয়েছে",
	Route: "রুট",
	Targets: "টার্গেট",
	Expense: "খরচ",
	Salary: "বেতন",
}

const DICT = { hi, bn }

/** Translate an English string. Unknown strings pass through unchanged. */
export function t(s) {
	if (locale.value === "en") return s
	return DICT[locale.value]?.[s] ?? s
}
