import { redirect } from "next/navigation";

/** The multi-skill adaptive assessment is the primary placement flow. */
export default function PlacementPage() {
  redirect("/placement/cefr");
}
