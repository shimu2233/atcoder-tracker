import BookmarkAddOutlinedIcon from "@mui/icons-material/BookmarkAddOutlined";
import BookmarkRemoveRoundedIcon from "@mui/icons-material/BookmarkRemoveRounded";
import OpenInNewRoundedIcon from "@mui/icons-material/OpenInNewRounded";
import SearchRoundedIcon from "@mui/icons-material/SearchRounded";
import {
  Alert,
  Button,
  Card,
  CardContent,
  Chip,
  InputAdornment,
  LinearProgress,
  MenuItem,
  Stack,
  Tab,
  Tabs,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Typography
} from "@mui/material";
import { useMemo, useState } from "react";
import type { LearningContentData, ProblemItem } from "./types";

const statusColor = (status: ProblemItem["status"]) => {
  if (status === "AC済み") return "success";
  if (status === "未AC") return "warning";
  return "default";
};

export function ProblemExplorer({
  data,
  csrfToken
}: {
  data: LearningContentData;
  csrfToken: string;
}) {
  const [section, setSection] = useState("すべて");
  const [status, setStatus] = useState("すべて");
  const [query, setQuery] = useState("");
  const [items, setItems] = useState(() => data.sections.flatMap((group) =>
    group.items.map((item) => ({ ...item, section: group.name }))
  ));

  const visibleItems = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();
    return items.filter((item) => {
      const matchesSection = section === "すべて" || item.section === section;
      const matchesStatus = status === "すべて" || item.status === status;
      const matchesQuery =
        !normalizedQuery ||
        item.name.toLowerCase().includes(normalizedQuery) ||
        item.problem_index.toLowerCase().includes(normalizedQuery) ||
        item.category.toLowerCase().includes(normalizedQuery);
      return matchesSection && matchesStatus && matchesQuery;
    });
  }, [items, query, section, status]);

  const acCount = items.filter((item) => item.status === "AC済み").length;
  const attemptedCount = items.filter((item) => item.status !== "未提出").length;
  const progress = items.length ? Math.round((acCount / items.length) * 100) : 0;

  const toggleDoLater = async (item: ProblemItem) => {
    const response = await fetch(item.toggle_url, {
      method: "POST",
      headers: { "X-CSRFToken": csrfToken },
      credentials: "same-origin"
    });
    if (!response.ok) return;
    setItems((current) =>
      current.map((candidate) =>
        candidate.problem_id === item.problem_id
          ? { ...candidate, is_do_later: !candidate.is_do_later }
          : candidate
      )
    );
  };

  return (
    <Stack spacing={3}>
      {!data.has_membership_data && (
        <Alert severity="info">問題一覧データがありません。fetch_problemsを実行してください。</Alert>
      )}

      <Card>
        <CardContent>
          <Stack spacing={1.25}>
            <Stack direction="row" justifyContent="space-between" alignItems="baseline">
              <Typography fontWeight={800}>AC進捗</Typography>
              <Typography color="text.secondary">
                {acCount} / {items.length}問（{progress}%）
              </Typography>
            </Stack>
            <LinearProgress variant="determinate" value={progress} sx={{ height: 10, borderRadius: 999 }} />
            <Typography variant="body2" color="text.secondary">
              着手 {attemptedCount}問・後でやる {items.filter((item) => item.is_do_later).length}問
            </Typography>
          </Stack>
        </CardContent>
      </Card>

      <Card>
        <Tabs
          value={section}
          onChange={(_, value) => setSection(value)}
          variant="scrollable"
          scrollButtons="auto"
          sx={{ px: 2, borderBottom: 1, borderColor: "divider" }}
        >
          <Tab value="すべて" label="すべて" />
          {data.sections.map((group) => (
            <Tab key={group.name} value={group.name} label={group.name} />
          ))}
        </Tabs>
        <CardContent>
          <Stack direction={{ xs: "column", md: "row" }} spacing={2} sx={{ mb: 2 }}>
            <TextField
              fullWidth
              size="small"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="問題番号・問題名・分野で検索"
              slotProps={{
                input: {
                  startAdornment: (
                    <InputAdornment position="start"><SearchRoundedIcon /></InputAdornment>
                  )
                }
              }}
            />
            <TextField
              select
              size="small"
              label="状態"
              value={status}
              onChange={(event) => setStatus(event.target.value)}
              sx={{ minWidth: 150 }}
            >
              {['すべて', '未提出', '未AC', 'AC済み'].map((value) => (
                <MenuItem key={value} value={value}>{value}</MenuItem>
              ))}
            </TextField>
          </Stack>

          <TableContainer sx={{ overflowX: "auto" }}>
            <Table size="small" aria-label="問題一覧">
              <TableHead>
                <TableRow>
                  <TableCell>問題</TableCell>
                  <TableCell>問題名</TableCell>
                  <TableCell>分野</TableCell>
                  <TableCell align="right">難易度</TableCell>
                  <TableCell>状態</TableCell>
                  <TableCell align="center">後でやる</TableCell>
                  <TableCell align="center">開く</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {visibleItems.map((item) => (
                  <TableRow key={`${item.section}-${item.problem_id}`} hover>
                    <TableCell sx={{ whiteSpace: "nowrap", fontWeight: 700 }}>
                      {item.problem_index}
                    </TableCell>
                    <TableCell>{item.name}</TableCell>
                    <TableCell>{item.category || "-"}</TableCell>
                    <TableCell align="right">{item.difficulty ?? "-"}</TableCell>
                    <TableCell>
                      <Chip size="small" color={statusColor(item.status)} label={item.status} />
                    </TableCell>
                    <TableCell align="center" sx={{ whiteSpace: "nowrap" }}>
                      <Button
                        size="small"
                        onClick={() => toggleDoLater(item)}
                        startIcon={item.is_do_later ? <BookmarkRemoveRoundedIcon /> : <BookmarkAddOutlinedIcon />}
                      >
                        {item.is_do_later ? "解除" : "後でやる"}
                      </Button>
                    </TableCell>
                    <TableCell align="center" sx={{ whiteSpace: "nowrap" }}>
                      <Button
                        size="small"
                        component="a"
                        href={item.url}
                        target="_blank"
                        rel="noreferrer"
                        endIcon={<OpenInNewRoundedIcon />}
                      >
                        開く
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
                {!visibleItems.length && (
                  <TableRow>
                    <TableCell colSpan={7} align="center" sx={{ py: 5, color: "text.secondary" }}>
                      条件に一致する問題はありません。
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </TableContainer>
        </CardContent>
      </Card>
    </Stack>
  );
}
