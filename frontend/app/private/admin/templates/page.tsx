import {
  getTemplateDetailAction,
  listTemplateCategoriesAction,
  listTemplatesAction,
} from "./actions";
import { TemplatesClient } from "./templates-client";

export default async function AdminTemplatesPage() {
  const [templates, categories] = await Promise.all([
    listTemplatesAction(),
    listTemplateCategoriesAction(),
  ]);

  const firstTemplateId = templates[0]?.id ?? null;
  const initialDetail = firstTemplateId
    ? await getTemplateDetailAction(firstTemplateId)
    : null;

  return (
    <TemplatesClient
      initialTemplates={templates}
      initialSelectedTemplateId={firstTemplateId}
      initialDetail={initialDetail}
      initialCategories={categories}
    />
  );
}
