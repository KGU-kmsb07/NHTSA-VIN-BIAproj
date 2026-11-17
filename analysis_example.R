# ==============================================================================
# 연구 과제: 한국 생산 수출 자동차의 리콜 위험 예측과 품질 관리 (NHTSA 자료를 중심으로)
# 스크립트: 3대 핵심 가치 실증 클러스터링 및 품질 관리 분석 예제 (V2.0 Pure Fact-based)
# 파일명: dataset/analysis_example.R
# ==============================================================================

# 1. 데이터 로드
rds_path <- "dataset/rds/master_vehicle_system_2020.rds"
parts_path <- "dataset/rds/master_parts_recalls_2020.rds"

if (!file.exists(rds_path)) {
  stop("데이터셋 파일이 존재하지 않습니다. dataset/build_py/run_pipeline.py를 먼저 실행하세요.")
}

df <- readRDS(rds_path)
cat(sprintf(">> 마스터 데이터셋 A 로드 완료: %d행 x %d열\n", nrow(df), ncol(df)))

# ------------------------------------------------------------------------------
# [가치 1] 조기 경보 (Early Warning): 화재 중심 vs 충돌/사상자 중심 군집 분류
# ------------------------------------------------------------------------------
cat("\n=======================================================\n")
cat(">> [가치 1] 비지도 학습(K-Means) 기반 위험 특성 군집화\n")
cat("=======================================================\n")

# 순수 팩트 카운트 변수 선택 (임의 가중치 배제)
cluster_vars <- c("fire_count", "crash_count", "inj_count", "death_count", "recall_count", "cmpl_count")
cluster_data <- df[, cluster_vars]

# 표준화 (Z-score Scaling)
scaled_data <- scale(cluster_data)

# K-Means 군집 분석 (4개 군집)
set.seed(42)
km_model <- kmeans(scaled_data, centers = 4, nstart = 25)
df$cluster <- as.factor(km_model$cluster)

# 군집별 프로파일 평균 확인
cluster_profile <- aggregate(cbind(fire_count, crash_count, inj_count, death_count, recall_count, cmpl_count) ~ cluster, 
                             data = df, mean)
cluster_size <- as.data.frame(table(df$cluster))
names(cluster_size) <- c("cluster", "n_obs")
profile_summary <- merge(cluster_size, cluster_profile, by = "cluster")

cat(">> 군집별 평균 특성 프로파일:\n")
num_cols <- names(profile_summary)[names(profile_summary) != "cluster"]
profile_summary[num_cols] <- lapply(profile_summary[num_cols], function(x) round(as.numeric(x), 2))
print(profile_summary)

# ------------------------------------------------------------------------------
# [가치 2] 공급사 및 조립공장 점검 (SCM & Assembly Plant Quality Audit)
# ------------------------------------------------------------------------------
cat("\n=======================================================\n")
cat(">> [가치 2] 한국 7대 조립공장별 결함 특성 및 리콜 위험 분석\n")
cat("=======================================================\n")

plant_audit <- aggregate(cbind(cmpl_count, fire_count, crash_count, recall_count) ~ plant_name + plant_city, 
                         data = df, sum)
plant_audit <- plant_audit[order(-plant_audit$recall_count), ]
print(plant_audit)

# ------------------------------------------------------------------------------
# [가치 3] 특정 부품/제품군 개선 건의 (Part & System Quality Engineering)
# ------------------------------------------------------------------------------
cat("\n=======================================================\n")
cat(">> [가치 3] 전면 부품 교체(is_part_replacement == 1) 상위 부품 도출\n")
cat("=======================================================\n")

if (file.exists(parts_path)) {
  parts_df <- readRDS(parts_path)
  
  # 전면 부품 교체(is_part_replacement == 1) 대상 중 리콜 규모(potaff) 상위 10개 부품
  replacement_parts <- parts_df[parts_df$is_part_replacement == 1, ]
  replacement_parts <- replacement_parts[order(-replacement_parts$potaff), ]
  
  top_parts <- head(replacement_parts[, c("mfr_comp_ptno", "mfr_comp_name", "make", "system", "potaff", "affected_models")], 10)
  print(top_parts)
}

cat("\n>> [완료] 3대 핵심 가치 실증 분석이 성공적으로 실행되었습니다.\n")
