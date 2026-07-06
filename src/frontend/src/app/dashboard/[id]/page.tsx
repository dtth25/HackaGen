import { StudyPackDashboardClient } from "@/components/course/StudyPackDashboardClient";

interface PageProps {
  params: Promise<{ id: string }>;
}

export default async function DashboardPage({ params }: PageProps) {
  const { id } = await params;
  return <StudyPackDashboardClient courseId={id} />;
}
