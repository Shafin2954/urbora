import { useState } from 'react'

/**
 * Sidebar: new chat, recent chats, saved crops, and the account row.
 *
 * Order is the point. The new-chat button is the one action that always makes
 * sense, so it is first; the recent-chat list sits directly under it because
 * that is the only other thing a returning farmer comes here for. Account
 * controls — name, settings, sign out — sit pinned at the bottom, out of the
 * way of both.
 *
 * The recent list used to stretch: `.sidebar-section:first-of-type` was
 * `flex: 1 1 auto`, so with one session the single row inflated into a large
 * empty card that read like a broken panel. It is content-height now and
 * scrolls past a cap instead.
 */

const fields = ['crop', 'district', 'area', 'area_unit', 'soil_type', 'water_source', 'budget_bdt', 'season']
const labels = { crop: 'ফসলের নাম', district: 'জেলা', area: 'জমির পরিমাণ', area_unit: 'জমির একক', soil_type: 'মাটির ধরন', water_source: 'পানির উৎস', budget_bdt: 'বাজেট', season: 'মৌসুম' }
const cropNames = { boro_rice: 'বোরো ধান', aman_rice: 'আমন ধান', potato: 'আলু', mustard: 'সরিষা', lentil: 'মসুর' }

/** First letter of the email — an avatar that needs no upload and no service. */
const initial = (email) => (email ?? '?').trim().charAt(0).toUpperCase()

export default function Sidebar({
  crops, activeCropId, onSelect, onCreate, onUpdate, onDelete, onSignOut,
  user, t, onOpenSettings,
}) {
  const [editing, setEditing] = useState(null)
  const [open, setOpen] = useState(false)

  const cropName = (crop) => cropNames[crop.label] ?? (crop.label === 'New consultation' ? t('sidebar.noCropChosen') : crop.label)
  const chatTitle = (crop) => (crop.title === 'New consultation' || !crop.title ? t('sidebar.untitled') : crop.title)

  const save = async (event) => {
    event.preventDefault()
    const data = Object.fromEntries(new FormData(event.currentTarget))
    await onUpdate(editing.id, Object.fromEntries(fields.map((key) => [key, data.get(key) || null])))
    setEditing(null)
  }

  const namedCrops = crops.filter((crop) => crop.crop || crop.profile?.last_crop)

  return <>
    <button className="sidebar-toggle" onClick={() => setOpen(!open)} aria-label={t('sidebar.list')}>☰</button>
    <aside className={`sidebar${open ? ' is-open' : ''}`}>
      <div className="sidebar-head">
        <button onClick={onCreate}>{t('sidebar.newChat')}</button>
      </div>

      {/* Recent chats. The server already returns updated_at DESC, so the
          session being worked on is the top row without any sorting here. */}
      <section className="sidebar-section sidebar-recent">
        <h2>{t('sidebar.recent')}</h2>
        <div className="crop-list">
          {crops.map((crop) => (
            <div className={`crop-row${crop.id === activeCropId ? ' is-active' : ''}`} key={crop.id}>
              <button className="crop-select" onClick={() => { onSelect(crop.id); setOpen(false) }}>
                <span className="crop-glyph" aria-hidden="true">▤</span>
                <span>
                  <strong>{chatTitle(crop)}</strong>
                  <small>{[crop.profile?.district, crop.profile?.area && `${crop.profile.area} ${crop.profile.area_unit ?? ''}`].filter(Boolean).join(' · ') || t('sidebar.startChat')}</small>
                </span>
              </button>
              <button className="crop-menu" onClick={() => setEditing(crop)} aria-label={t('sidebar.edit')}>⋯</button>
            </div>
          ))}
        </div>
      </section>

      <section className="sidebar-section sidebar-crops">
        <h2>{t('sidebar.myCrops')}</h2>
        {namedCrops.length ? (
          <div className="crop-list">
            {namedCrops.map((crop) => (
              <button className="saved-crop" key={crop.id} onClick={() => setEditing(crop)}>
                <span className="crop-glyph" aria-hidden="true">◉</span>
                <span>
                  <strong>{cropName(crop)}</strong>
                  <small>{[crop.profile?.district, crop.profile?.soil_type, crop.profile?.season].filter(Boolean).join(' · ') || t('sidebar.editHint')}</small>
                </span>
              </button>
            ))}
          </div>
        ) : <p className="sidebar-empty">{t('sidebar.noCrops')}</p>}
      </section>

      <div className="sidebar-account">
        <span className="avatar" aria-hidden="true">{initial(user?.email)}</span>
        <span className="account-name" title={user?.email}>{user?.email ?? ''}</span>
        <button className="icon-button" onClick={onOpenSettings} aria-label={t('sidebar.settings')} title={t('sidebar.settings')}>⚙</button>
        <button className="icon-button" onClick={onSignOut} aria-label={t('sidebar.signOut')} title={t('sidebar.signOut')}>⏻</button>
      </div>
    </aside>

    {editing && <div className="modal-backdrop">
      <form className="crop-form" onSubmit={save}>
        <h2>ফসলের তথ্য</h2>
        {fields.map((field) => (
          <label key={field}>{labels[field]}
            <input className="field" name={field} defaultValue={field === 'crop' ? editing.crop ?? '' : editing.profile?.[field] ?? ''} />
          </label>
        ))}
        <div>
          <button>সংরক্ষণ</button>
          <button type="button" className="secondary" onClick={() => setEditing(null)}>বাতিল</button>
          <button type="button" className="danger" onClick={async () => { if (window.confirm('এই ফসলটি মুছবেন?')) { await onDelete(editing.id); setEditing(null) } }}>মুছুন</button>
        </div>
      </form>
    </div>}
  </>
}
