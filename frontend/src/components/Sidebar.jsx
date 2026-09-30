import { useState } from 'react'
import { Lockup } from './BrandMark.jsx'

/**
 * Sidebar: new chat, previous chats, saved crops (accounts only), and the account row.
 *
 * Order is the point. "New chat" is the one action that always makes sense, so it is first;
 * the previous-chats list sits directly under it because that is the only other thing a
 * returning farmer comes here for. Account controls sit pinned at the bottom.
 *
 * It serves both kinds of visitor. An account's chats come from /api/crops (Supabase, per
 * user); a guest's chats are remembered in this browser (useGuestSessions). The rows look the
 * same, so signing in changes where the list is kept, not how it reads.
 */

const fields = ['crop', 'district', 'area', 'area_unit', 'soil_type', 'water_source', 'budget_bdt', 'season']
const labels = { crop: 'ফসলের নাম', district: 'জেলা', area: 'জমির পরিমাণ', area_unit: 'জমির একক', soil_type: 'মাটির ধরন', water_source: 'পানির উৎস', budget_bdt: 'বাজেট', season: 'মৌসুম' }
const cropNames = { boro_rice: 'বোরো ধান', aman_rice: 'আমন ধান', potato: 'আলু', mustard: 'সরিষা', lentil: 'মসুর' }

/** First letter of the email: an avatar that needs no upload and no service. */
const initial = (email) => (email ?? '?').trim().charAt(0).toUpperCase()

/** "আজ", "গতকাল" or a short date, from an ISO timestamp. */
function when(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  const days = Math.floor((Date.now() - d.getTime()) / 86400000)
  if (days <= 0) return 'আজ'
  if (days === 1) return 'গতকাল'
  return d.toLocaleDateString('bn-BD', { day: 'numeric', month: 'short' })
}

export default function Sidebar({
  chats, activeId, onSelect, onCreate, onDelete,
  crops = [], onUpdate, guest, user, onSignIn, onSignOut, onOpenSettings, t,
}) {
  const [editing, setEditing] = useState(null)
  const [open, setOpen] = useState(false)

  const cropName = (crop) => cropNames[crop.label] ?? (crop.label === 'New consultation' ? t('sidebar.noCropChosen') : crop.label)

  const save = async (event) => {
    event.preventDefault()
    const data = new FormData(event.currentTarget)
    await onUpdate(editing.id, Object.fromEntries(fields.map((key) => [key, data.get(key) || null])))
    setEditing(null)
  }

  const namedCrops = crops.filter((crop) => crop.crop || crop.profile?.last_crop)
  const pick = (id) => { onSelect(id); setOpen(false) }

  return <>
    <button className="sidebar-toggle" onClick={() => setOpen(!open)} aria-label={t('sidebar.list')} aria-expanded={open}>
      <span /><span /><span />
    </button>
    {open && <div className="sidebar-scrim" onClick={() => setOpen(false)} aria-hidden="true" />}
    <aside className={`sidebar${open ? ' is-open' : ''}`} aria-label={t('sidebar.recent')}>
      <a className="sidebar-brand" href="#/" aria-label="উর্বরা, প্রথম পাতা"><Lockup size={38} /></a>
      <button className="sidebar-new" onClick={() => { onCreate(); setOpen(false) }}>
        <span aria-hidden="true">＋</span> {t('sidebar.newChatPlain')}
      </button>

      <section className="sidebar-section sidebar-recent">
        <h2>{t('sidebar.recent')}</h2>
        {chats.length ? (
          <ul className="chat-list">
            {chats.map((chat) => (
              <li key={chat.id} className={`chat-row${chat.id === activeId ? ' is-active' : ''}`}>
                <button className="chat-select" onClick={() => pick(chat.id)} aria-current={chat.id === activeId ? 'true' : undefined}>
                  <strong>{chat.title || t('sidebar.untitled')}</strong>
                  <small>{[chat.subtitle, when(chat.updated)].filter(Boolean).join(' · ') || t('sidebar.startChat')}</small>
                </button>
                {chat.editable
                  ? <button className="chat-menu" onClick={() => setEditing(crops.find((c) => c.id === chat.id))} aria-label={t('sidebar.edit')} title={t('sidebar.edit')}>⋯</button>
                  : onDelete && <button className="chat-menu" onClick={() => onDelete(chat.id)} aria-label={t('sidebar.remove')} title={t('sidebar.remove')}>×</button>}
              </li>
            ))}
          </ul>
        ) : <p className="sidebar-empty">{t('sidebar.noChats')}</p>}
      </section>

      {!guest && (
        <section className="sidebar-section sidebar-crops">
          <h2>{t('sidebar.myCrops')}</h2>
          {namedCrops.length ? (
            <ul className="chat-list">
              {namedCrops.map((crop) => (
                <li key={crop.id} className="chat-row">
                  <button className="chat-select" onClick={() => setEditing(crop)}>
                    <strong>{cropName(crop)}</strong>
                    <small>{[crop.profile?.district, crop.profile?.soil_type, crop.profile?.season].filter(Boolean).join(' · ') || t('sidebar.editHint')}</small>
                  </button>
                </li>
              ))}
            </ul>
          ) : <p className="sidebar-empty">{t('sidebar.noCrops')}</p>}
        </section>
      )}

      <div className="sidebar-account">
        {guest ? <>
          <span className="avatar avatar-guest" aria-hidden="true">অ</span>
          <span className="account-name">
            <b>{t('sidebar.guest')}</b>
            <small>{t('sidebar.guestNote')}</small>
          </span>
          {onSignIn && <button className="account-signin" onClick={onSignIn}>{t('sidebar.signIn')}</button>}
        </> : <>
          <span className="avatar" aria-hidden="true">{initial(user?.email)}</span>
          <span className="account-name" title={user?.email}><b>{user?.email ?? ''}</b></span>
          <button className="icon-button" onClick={onOpenSettings} aria-label={t('sidebar.settings')} title={t('sidebar.settings')}>⚙</button>
          <button className="icon-button" onClick={onSignOut} aria-label={t('sidebar.signOut')} title={t('sidebar.signOut')}>⏻</button>
        </>}
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
          <button type="button" className="danger" onClick={async () => { if (window.confirm('এই আলাপটি মুছবেন?')) { await onDelete(editing.id); setEditing(null) } }}>মুছুন</button>
        </div>
      </form>
    </div>}
  </>
}
