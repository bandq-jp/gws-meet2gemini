-- Guard the meet.link_meeting_by_title trigger so that missing auxiliary tables
-- (applications/application_events/applicant_meetings) do not break inserts
-- into meeting_documents.

create schema if not exists meet;

create or replace function meet.link_meeting_by_title()
returns trigger
language plpgsql
as $function$
declare
  chosen_applicant uuid;
begin
  -- If applicant linkage tables are absent, skip gracefully.
  if to_regclass('public.applications') is null
     or to_regclass('public.application_events') is null
     or to_regclass('meet.applicant_meetings') is null then
    return new;
  end if;

  with candidates as (
    select
      a.applicant_id,
      ev.event_date,
      case
        when new.meeting_datetime is null or ev.event_date is null
          then null
        else abs((new.meeting_datetime::date - ev.event_date))
      end as day_diff
    from public.applications a
    join public.application_events ev on ev.application_id = a.id
    where ev.event_title is not null
      and (
            lower(new.title) like '%' || lower(ev.event_title) || '%'
         or lower(ev.event_title) like '%' || lower(new.title) || '%'
      )
      and (
            new.meeting_datetime is null
         or ev.event_date between (new.meeting_datetime::date - interval '3 day')
                                and (new.meeting_datetime::date + interval '3 day')
      )
  ),
  ranked as (
    select applicant_id,
           day_diff,
           row_number() over (order by day_diff asc nulls last) as rn,
           count(*) over (order by day_diff asc nulls last
                          rows between unbounded preceding and unbounded following) as total_cnt
    from candidates
  ),
  top1 as (
    select applicant_id, day_diff
    from ranked
    where rn = 1
  ),
  top2 as (
    select applicant_id, day_diff
    from ranked
    where rn = 2
  )
  select t1.applicant_id
    into chosen_applicant
  from top1 t1
  left join top2 t2 on true
  where not (
    t2.applicant_id is not null and coalesce(t1.day_diff, -1) = coalesce(t2.day_diff, -1)
  );

  if chosen_applicant is null then
    return new;
  end if;

  insert into meet.applicant_meetings (applicant_id, meeting_id, matched_by)
  values (chosen_applicant, new.id, 'title')
  on conflict do nothing;

  return new;
end;
$function$;
