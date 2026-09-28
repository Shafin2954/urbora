/**
 * UI chrome strings only — buttons, headings, tab labels, settings.
 *
 * Deliberately NOT a translation layer for advice. Everything the farmer is
 * told about their farm comes from the agent, which writes in whichever
 * language the setting asks for (backend/agent/prompts.py), and from tool
 * output that carries its own Bangla text. Translating those here would create
 * a second, silently-diverging copy of the advice.
 *
 * Bangla is the default and the fallback: a missing English key shows Bangla
 * rather than a raw key name, because a farmer seeing `sidebar.newChat` is a
 * worse failure than a farmer seeing Bangla.
 */

const bn = {
  'app.loading': 'লোড হচ্ছে…',
  'sidebar.newChat': '+ নতুন আলাপ',
  'sidebar.recent': 'সাম্প্রতিক আলাপ',
  'sidebar.myCrops': 'আমার ফসল',
  'sidebar.untitled': 'নতুন আলাপ',
  'sidebar.startChat': 'আলাপ শুরু করুন',
  'sidebar.noCrops': 'আলাপে ফসল নির্ধারিত হলে এখানে দেখা যাবে।',
  'sidebar.noCropChosen': 'ফসল নির্ধারিত হয়নি',
  'sidebar.editHint': 'তথ্য দেখুন ও সম্পাদনা করুন',
  'sidebar.edit': 'সম্পাদনা',
  'sidebar.settings': 'সেটিংস',
  'sidebar.signOut': 'সাইন আউট',
  'sidebar.list': 'ফসল তালিকা',

  'tab.chat': 'কথা বলুন',
  'tab.finance': 'হিসাব',
  'tab.plan': 'পরিকল্পনা',
  'tab.checkout': 'কেনাকাটা',
  'tab.graph': 'চিত্র',

  'pane.finance': 'হিসাব',
  'pane.plan': 'মৌসুম পরিকল্পনা',
  'pane.graph': 'কাজের চিত্র',

  'chat.placeholder': 'এখানে লিখুন…',
  'chat.send': 'পাঠান',
  'chat.failed': 'দুঃখিত, এখন উত্তর দিতে পারছি না। একটু পরে আবার চেষ্টা করুন।',
  'chat.failedDetail': 'কারিগরি তথ্য',
  'chat.mic': 'কথা বলে লিখুন',
  'chat.micStop': 'থামুন',
  'chat.listening': 'শুনছি… (থামাতে আবার চাপুন)',
  'chat.transcribing': 'লেখা হচ্ছে…',
  'chat.speak': 'পড়ে শোনান',
  'chat.speakStop': 'থামুন',
  'chat.micUnsupported': 'এই ব্রাউজারে কণ্ঠস্বর সমর্থিত নয়',

  'start.title': 'শুরু করুন',
  'start.body': 'একটি নতুন আলাপ শুরু করুন।',
  'start.useSidebar': 'বাম পাশের নতুন আলাপ বাটন ব্যবহার করুন।',

  'settings.title': 'সেটিংস',
  'settings.language': 'ভাষা',
  'settings.languageNote': 'উত্তরও এই ভাষায় আসবে।',
  'settings.bangla': 'বাংলা',
  'settings.english': 'English',
  'settings.fontSize': 'লেখার আকার',
  'settings.small': 'ছোট',
  'settings.medium': 'মাঝারি',
  'settings.large': 'বড়',
  'settings.voice': 'কণ্ঠস্বর',
  'settings.voiceNote': 'কণ্ঠস্বরগুলো আপনার ব্রাউজার ও ফোন থেকে আসে।',
  'settings.voiceDefault': 'ডিফল্ট',
  'settings.voiceNone': 'এই ব্রাউজারে কোনো কণ্ঠস্বর পাওয়া যায়নি।',
  'settings.speed': 'পড়ার গতি',
  'settings.close': 'বন্ধ করুন',
  'settings.reset': 'আগের অবস্থায়',
}

const en = {
  'app.loading': 'Loading…',
  'sidebar.newChat': '+ New chat',
  'sidebar.recent': 'Recent chats',
  'sidebar.myCrops': 'My crops',
  'sidebar.untitled': 'New chat',
  'sidebar.startChat': 'Start the conversation',
  'sidebar.noCrops': 'Crops appear here once a conversation settles on one.',
  'sidebar.noCropChosen': 'No crop chosen yet',
  'sidebar.editHint': 'View and edit details',
  'sidebar.edit': 'Edit',
  'sidebar.settings': 'Settings',
  'sidebar.signOut': 'Sign out',
  'sidebar.list': 'Crop list',

  'tab.chat': 'Chat',
  'tab.finance': 'Finance',
  'tab.plan': 'Plan',
  'tab.checkout': 'Checkout',
  'tab.graph': 'Graph',

  'pane.finance': 'Finance',
  'pane.plan': 'Season plan',
  'pane.graph': "Agent's work",

  'chat.placeholder': 'Type here…',
  'chat.send': 'Send',
  'chat.failed': 'Sorry, I cannot answer right now. Please try again in a little while.',
  'chat.failedDetail': 'Technical detail',
  'chat.mic': 'Speak instead of typing',
  'chat.micStop': 'Stop',
  'chat.listening': 'Listening… (tap again to stop)',
  'chat.transcribing': 'Writing it down…',
  'chat.speak': 'Read aloud',
  'chat.speakStop': 'Stop',
  'chat.micUnsupported': 'Voice input is not supported in this browser',

  'start.title': 'Get started',
  'start.body': 'Start a new conversation.',
  'start.useSidebar': 'Use the New chat button on the left.',

  'settings.title': 'Settings',
  'settings.language': 'Language',
  'settings.languageNote': 'Replies come back in this language too.',
  'settings.bangla': 'বাংলা',
  'settings.english': 'English',
  'settings.fontSize': 'Text size',
  'settings.small': 'Small',
  'settings.medium': 'Medium',
  'settings.large': 'Large',
  'settings.voice': 'Voice',
  'settings.voiceNote': 'Voices come from your browser and phone.',
  'settings.voiceDefault': 'Default',
  'settings.voiceNone': 'This browser offers no speech voices.',
  'settings.speed': 'Reading speed',
  'settings.close': 'Close',
  'settings.reset': 'Reset',
}

const TABLES = { bn, en }

/** Build a lookup for one language. Falls back to Bangla, then to the key. */
export function translator(language) {
  const table = TABLES[language] ?? bn
  return (key) => table[key] ?? bn[key] ?? key
}
