import { useState } from 'react'

const fields = ['crop', 'district', 'area', 'area_unit', 'soil_type', 'water_source', 'budget_bdt', 'season']
const labels = { crop: 'ফসলের নাম', district: 'জেলা', area: 'জমির পরিমাণ', area_unit: 'জমির একক', soil_type: 'মাটির ধরন', water_source: 'পানির উৎস', budget_bdt: 'বাজেট', season: 'মৌসুম' }
const cropNames = { boro_rice: 'বোরো ধান', aman_rice: 'আমন ধান', potato: 'আলু', mustard: 'সরিষা', lentil: 'মসুর' }
const cropName = (crop) => cropNames[crop.label] ?? (crop.label === 'New consultation' ? 'ফসল নির্ধারিত হয়নি' : crop.label)
const chatTitle = (crop) => crop.title === 'New consultation' ? 'নতুন আলাপ' : crop.title
export default function Sidebar({ crops, activeCropId, onSelect, onCreate, onUpdate, onDelete, onSignOut }) {
  const [editing, setEditing] = useState(null)
  const [open, setOpen] = useState(false)
  const save = async (event) => { event.preventDefault(); const data = Object.fromEntries(new FormData(event.currentTarget)); await onUpdate(editing.id, Object.fromEntries(fields.map((key) => [key, data.get(key) || null]))); setEditing(null) }
  const namedCrops = crops.filter((crop) => crop.crop || crop.profile?.last_crop)
  return <><button className="sidebar-toggle" onClick={() => setOpen(!open)} aria-label="ফসল তালিকা">☰</button><aside className={`sidebar${open ? ' is-open' : ''}`}>
    <div className="sidebar-head"><button onClick={onCreate}>+ নতুন আলাপ</button></div>
    <section className="sidebar-section"><h2>আমার আলাপ</h2><div className="crop-list">{crops.map((crop) => <div className={`crop-row${crop.id === activeCropId ? ' is-active' : ''}`} key={crop.id}>
      <button className="crop-select" onClick={() => { onSelect(crop.id); setOpen(false) }}><span className="crop-glyph">◉</span><span><strong>{chatTitle(crop)}</strong><small>{[crop.profile?.district, crop.profile?.area && `${crop.profile.area} ${crop.profile.area_unit ?? ''}`].filter(Boolean).join(' · ') || 'আলাপ শুরু করুন'}</small></span></button>
      <button className="crop-menu" onClick={() => setEditing(crop)} aria-label="সম্পাদনা">⋯</button></div>)}</div></section>
    <section className="sidebar-section sidebar-crops"><h2>আমার ফসল</h2>{namedCrops.length ? <div className="crop-list">{namedCrops.map((crop) => <button className="saved-crop" key={crop.id} onClick={() => setEditing(crop)}><span className="crop-glyph">◉</span><span><strong>{cropName(crop)}</strong><small>{[crop.profile?.district, crop.profile?.soil_type, crop.profile?.season].filter(Boolean).join(' · ') || 'তথ্য দেখুন ও সম্পাদনা করুন'}</small></span></button>)}</div> : <p className="sidebar-empty">আলাপে ফসল নির্ধারিত হলে এখানে দেখা যাবে।</p>}</section>
    <button className="signout" onClick={onSignOut}>সাইন আউট</button>
  </aside>{editing && <div className="modal-backdrop"><form className="crop-form" onSubmit={save}><h2>ফসলের তথ্য</h2>{fields.map((field) => <label key={field}>{labels[field]}<input className="field" name={field} defaultValue={field === 'crop' ? editing.crop ?? '' : editing.profile?.[field] ?? ''} /></label>)}<div><button>সংরক্ষণ</button><button type="button" className="secondary" onClick={() => setEditing(null)}>বাতিল</button><button type="button" className="danger" onClick={async () => { if (window.confirm('এই ফসলটি মুছবেন?')) { await onDelete(editing.id); setEditing(null) } }}>মুছুন</button></div></form></div>}</>
}
