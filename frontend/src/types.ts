export type LearningContentStat = {
  content_id: string;
  title: string;
  total: number;
  attempted: number;
  ac: number;
  attempt_rate: number;
  ac_rate: number;
  detail_url: string;
};

export type ProblemItem = {
  problem_id: string;
  problem_index: string;
  name: string;
  category: string;
  difficulty: number | null;
  status: "未提出" | "未AC" | "AC済み";
  is_do_later: boolean;
  url: string;
  toggle_url: string;
};

export type ProblemSection = {
  name: string;
  items: ProblemItem[];
};

export type LearningContentData = {
  content_id: string;
  title: string;
  has_membership_data: boolean;
  sections: ProblemSection[];
};

export type ContestProblemItem = {
  problem_id: string;
  problem_index: string;
  name: string;
  category: string;
  difficulty: number | null;
  status: "未提出" | "未AC" | "AC済み";
  is_do_later: boolean;
  url: string;
  toggle_url: string;
};

export type ContestItem = {
  contest_id: string;
  title: string;
  last_submitted_at: string;
  items: ContestProblemItem[];
};

export type ContestGroup = {
  series: string;
  label: string;
  contests: ContestItem[];
};

export type ContestCategory = {
  key: "algorithm" | "heuristic" | "grand";
  label: string;
  groups: ContestGroup[];
};

export type ContestExplorerData = {
  categories: ContestCategory[];
};

export type ProblemListData = {
  sections: ProblemSection[];
  empty_message: string;
  remove_when_unbookmarked: boolean;
};

export type CategoryStat = {
  category: string;
  total: number;
  attempted: number;
  ac: number;
  attempt_rate: number;
  ac_rate: number;
};

export type DifficultyStat = {
  band: string;
  total: number;
  ac: number;
  ac_rate: number;
};

export type DashboardData = {
  category_stats: CategoryStat[];
  difficulty_stats: DifficultyStat[];
  messages: string[];
  sync_url: string;
};
