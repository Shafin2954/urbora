import { Assumption } from './Provenance.jsx'

const LABELS = {
  land_prep: 'জমি প্রস্তুতি', sowing: 'রোপণ/বপন', irrigation: 'সেচ',
  fertilizer: 'সার', weeding: 'আগাছা', pest_checkpoint: 'বালাই পরীক্ষা',
  harvest: 'ফসল সংগ্রহ', other: 'অন্যান্য',
}

export default function PlanPanel({ plan }) {
  return (
    <div className="plan-list">
      {plan.tasks.map((task) => (
        <article className="plan-task" key={`${task.date}-${task.task}`}>
          <time className="mono">{task.date}</time>
          <div>
            <strong>{task.task}</strong>
            <span className="task-category">{LABELS[task.category]}</span>
            <p>{task.details}</p>
            {task.depends_on_weather && <p className="weather-note">আবহাওয়া দেখে কাজটি নিশ্চিত করুন।</p>}
            <Assumption prov={task.provenance} />
          </div>
        </article>
      ))}
    </div>
  )
}
