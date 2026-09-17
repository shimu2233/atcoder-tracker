import BookmarkAddOutlinedIcon from "@mui/icons-material/BookmarkAddOutlined";
import BookmarkRemoveRoundedIcon from "@mui/icons-material/BookmarkRemoveRounded";
import ExpandMoreRoundedIcon from "@mui/icons-material/ExpandMoreRounded";
import OpenInNewRoundedIcon from "@mui/icons-material/OpenInNewRounded";
import {
  Accordion,
  AccordionDetails,
  AccordionSummary,
  Alert,
  Box,
  Button,
  Chip,
  FormControl,
  InputLabel,
  MenuItem,
  Select,
  Stack,
  Tab,
  Tabs,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Typography
} from "@mui/material";
import { useMemo, useState } from "react";
import type { ContestExplorerData, ContestProblemItem } from "./types";

const statusColor = (status: ContestProblemItem["status"]) => {
  if (status === "AC済み") return "success";
  if (status === "未AC") return "warning";
  return "default";
};

export function ContestExplorer({
  data,
  csrfToken
}: {
  data: ContestExplorerData;
  csrfToken: string;
}) {
  const [categoryKey, setCategoryKey] = useState("algorithm");
  const [order, setOrder] = useState<"newest" | "oldest">("newest");
  const [items, setItems] = useState(data.categories);

  const category = items.find((candidate) => candidate.key === categoryKey) ?? items[0];
  const groups = useMemo(() => {
    if (!category) return [];
    return category.groups.map((group) => ({
      ...group,
      contests: [...group.contests].sort((left, right) => {
        const comparison = left.last_submitted_at.localeCompare(right.last_submitted_at);
        return order === "newest" ? -comparison : comparison;
      })
    }));
  }, [category, order]);

  const toggleDoLater = async (item: ContestProblemItem) => {
    const response = await fetch(item.toggle_url, {
      method: "POST",
      headers: { "X-CSRFToken": csrfToken },
      credentials: "same-origin"
    });
    if (!response.ok) return;
    setItems((current) => current.map((categoryItem) => ({
      ...categoryItem,
      groups: categoryItem.groups.map((group) => ({
        ...group,
        contests: group.contests.map((contest) => ({
          ...contest,
          items: contest.items.map((candidate) =>
            candidate.problem_id === item.problem_id
              ? { ...candidate, is_do_later: !candidate.is_do_later }
              : candidate
          )
        }))
      }))
    })));
  };

  const contestCount = groups.reduce((sum, group) => sum + group.contests.length, 0);

  return (
    <Stack spacing={3}>
      <Stack
        direction={{ xs: "column", md: "row" }}
        justifyContent="space-between"
        alignItems={{ md: "center" }}
        spacing={2}
      >
        <Tabs
          value={categoryKey}
          onChange={(_, value) => setCategoryKey(value)}
          variant="scrollable"
          scrollButtons="auto"
        >
          {items.map((categoryItem) => (
            <Tab key={categoryItem.key} value={categoryItem.key} label={categoryItem.label} />
          ))}
        </Tabs>
        <FormControl size="small" sx={{ minWidth: 140 }}>
          <InputLabel id="contest-order-label">結果の順番</InputLabel>
          <Select
            labelId="contest-order-label"
            value={order}
            label="結果の順番"
            onChange={(event) => setOrder(event.target.value as "newest" | "oldest")}
          >
            <MenuItem value="newest">新しい順</MenuItem>
            <MenuItem value="oldest">古い順</MenuItem>
          </Select>
        </FormControl>
      </Stack>

      {!contestCount && <Alert severity="info">この分類には提出済みのコンテストがありません。</Alert>}

      {groups.map((group) => (
        <Stack key={group.series} spacing={1.25}>
          <Typography variant="h6" component="h2">{group.label}</Typography>
          {group.contests.map((contest) => (
            <Accordion key={contest.contest_id} disableGutters>
              <AccordionSummary expandIcon={<ExpandMoreRoundedIcon />}>
                <Stack
                  direction={{ xs: "column", sm: "row" }}
                  alignItems={{ sm: "center" }}
                  spacing={{ xs: 0.25, sm: 1 }}
                  sx={{ minWidth: 0 }}
                >
                  <Typography fontWeight={700}>{contest.title}</Typography>
                  <Chip size="small" label={contest.contest_id} variant="outlined" />
                  <Typography variant="caption" color="text.secondary">
                    最終提出 {new Date(contest.last_submitted_at).toLocaleDateString("ja-JP")}
                  </Typography>
                </Stack>
              </AccordionSummary>
              <AccordionDetails sx={{ px: { xs: 0, sm: 2 } }}>
                <TableContainer sx={{ overflowX: "auto" }}>
                  <Table size="small" aria-label={`${contest.title}の問題一覧`}>
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
                      {contest.items.map((item) => (
                        <TableRow key={item.problem_id} hover>
                          <TableCell sx={{ fontWeight: 700 }}>{item.problem_index}</TableCell>
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
                              startIcon={item.is_do_later
                                ? <BookmarkRemoveRoundedIcon />
                                : <BookmarkAddOutlinedIcon />}
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
                    </TableBody>
                  </Table>
                </TableContainer>
              </AccordionDetails>
            </Accordion>
          ))}
        </Stack>
      ))}
    </Stack>
  );
}
