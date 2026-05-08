import type { SectionItem } from "@/schema/resume/data";

import { TiptapContent } from "@/components/input/rich-input";
import { filterFieldValues } from "@/utils/field";
import { stripHtml } from "@/utils/string";
import { cn } from "@/utils/style";

import { LinkedTitle } from "../linked-title";
import { PageLink } from "../page-link";

type EducationItemProps = SectionItem<"education"> & {
  className?: string;
};

export function EducationItem({ className, ...item }: EducationItemProps) {
  const degreeAndGrade = [item.degree, item.grade].filter(Boolean).join(" • ");
  const locationAndPeriod = [item.location, item.period].filter(Boolean).join(" • ");
  const headerValues = {
    school: item.school,
    degreeAndGrade,
    area: item.area,
    locationAndPeriod,
  };
  const headerFields = filterFieldValues(
    headerValues,
    {
      key: "school",
      content: (
        <LinkedTitle
          title={item.school}
          website={item.website}
          showLinkInTitle={item.options?.showLinkInTitle}
          className="section-item-title education-item-title"
        />
      ),
    },
    {
      key: "degreeAndGrade",
      content: <span className="section-item-metadata education-item-degree-grade">{degreeAndGrade}</span>,
    },
    {
      key: "area",
      content: <span className="section-item-metadata education-item-area">{item.area}</span>,
    },
    {
      key: "locationAndPeriod",
      content: <span className="section-item-metadata education-item-location-period">{locationAndPeriod}</span>,
    },
  );

  return (
    <div className={cn("education-item", className)}>
      {/* Header */}
      <div className="section-item-header education-item-header mb-2">
        <div className="flex items-start justify-between gap-x-2">
          <div className="flex min-w-0 flex-1 flex-col items-start">
            {headerFields.get("school")?.content}
            {headerFields.get("area")?.content}
          </div>

          <div className="flex min-w-0 shrink-0 flex-col items-end text-end">
            {headerFields.get("degreeAndGrade")?.content}
            {headerFields.get("locationAndPeriod")?.content}
          </div>
        </div>
      </div>

      {/* Description */}
      <div
        className={cn("section-item-description education-item-description", !stripHtml(item.description) && "hidden")}
      >
        <TiptapContent content={item.description} />
      </div>

      {/* Website */}
      {!item.options?.showLinkInTitle && (
        <div className="section-item-website education-item-website">
          <PageLink {...item.website} label={item.website.label} />
        </div>
      )}
    </div>
  );
}
