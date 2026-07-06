import { StudyPackDashboardClient } from "@/components/course/StudyPackDashboardClient";

interface PageProps {
  params: Promise<{ id: string }>;
}

export default async function CourseDetailPage({ params }: PageProps) {
  const { id } = await params;

  // Auth tokens only live in browser localStorage (see src/lib/auth.ts), so data
  // fetching must happen client-side (in StudyPackDashboardClient) rather than here
  // in this Server Component — a server-side fetch would never carry the
  // Authorization header and would always 401.
  return <StudyPackDashboardClient courseId={id} />;
}
