import type { SectionItem } from "@/schema/resume/data";

import { TiptapContent } from "@/components/input/rich-input";
import { filterFieldValues } from "@/utils/field";
import { stripHtml } from "@/utils/string";
import { cn } from "@/utils/style";

import { LinkedTitle } from "../linked-title";
import { PageLink } from "../page-link";

type VolunteerItemProps = SectionItem<"volunteer"> & {
  className?: string;
};

export function VolunteerItem({ className, ...item }: VolunteerItemProps) {
  const headerValues = {
    organization: item.organization,
    period: item.period,
    location: item.location,
  };
  const headerFields = filterFieldValues(
    headerValues,
    {
      key: "organization",
      content: (
        <LinkedTitle
          title={item.organization}
          website={item.website}
          showLinkInTitle={item.options?.showLinkInTitle}
          className="section-item-title volunteer-item-title"
        />
      ),
    },
    {
      key: "period",
      content: <span className="section-item-metadata volunteer-item-period">{item.period}</span>,
    },
    {
      key: "location",
      content: <span className="section-item-metadata volunteer-item-location">{item.location}</span>,
    },
  );

  return (
    <div className={cn("volunteer-item", className)}>
      {/* Header */}
      <div className="section-item-header volunteer-item-header">
        <div className="flex items-start justify-between gap-x-2">
          <div className="flex min-w-0 flex-1 flex-col items-start">
            {headerFields.get("organization")?.content}
            {headerFields.get("location")?.content}
          </div>

          <div className="flex min-w-0 shrink-0 flex-col items-end text-end">{headerFields.get("period")?.content}</div>
        </div>
      </div>

      {/* Description */}
      <div
        className={cn("section-item-description volunteer-item-description", !stripHtml(item.description) && "hidden")}
      >
        <TiptapContent content={item.description} />
      </div>

      {/* Website */}
      {!item.options?.showLinkInTitle && (
        <div className="section-item-website volunteer-item-website">
          <PageLink {...item.website} label={item.website.label} />
        </div>
      )}
    </div>
  );
}
