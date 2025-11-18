# AWS FIS 実験テンプレート作成・起動ツール

このツールは、AWS Fault Injection Simulator (FIS) を使用してLambda関数に障害を注入する実験テンプレートを作成・起動します。

## 機能

- **実験テンプレート作成**: Lambda関数に対する障害注入アクションを定義したFIS実験テンプレートを作成
- **実験起動**: 作成したテンプレートを使って実際に実験を開始
- **ステータス確認**: 実験の進行状況を取得

## 前提条件

1. **IAMロール**: FISが使用するIAMロールが必要です。`cfn/fis_lambda_role.yml` をデプロイして作成できます。

   ```bash
   cd /workspaces/aws_fis
   aws cloudformation deploy \
     --stack-name fis-lambda-role \
     --template-file cfn/fis_lambda_role.yml \
     --capabilities CAPABILITY_NAMED_IAM
   ```

2. **Python依存関係**:
   ```bash
   pip install boto3
   ```

3. **AWS認証情報**: AWS CLIの認証情報が設定されていること

## 使用方法

### 基本的な使い方

```bash
export AWS_ACCOUNT_ID=`aws sts get-caller-identity --output text --query Account`
python create_experiment_template.py \
  --role-arn arn:aws:iam::$AWS_ACCOUNT_ID:role/FisLambdaExperimentRole \
  --lambda-arns arn:aws:lambda:ap-northeast-1:$AWS_ACCOUNT_ID:function:my-function
```

### テンプレート作成のみ（実験は起動しない）

```bash
export AWS_ACCOUNT_ID=`aws sts get-caller-identity --output text --query Account`
python create_experiment_template.py \
  --role-arn arn:aws:iam::$AWS_ACCOUNT_ID:role/FisLambdaExperimentRole \
  --lambda-arns arn:aws:lambda:ap-northeast-1:$AWS_ACCOUNT_ID:function:my-function \
  --no-start
```

### 複数のLambda関数をターゲット

```bash
export AWS_ACCOUNT_ID=`aws sts get-caller-identity --output text --query Account`
python create_experiment_template.py \
  --role-arn arn:aws:iam::$AWS_ACCOUNT_ID:role/FisLambdaExperimentRole \
  --lambda-arns \
    arn:aws:lambda:ap-northeast-1:$AWS_ACCOUNT_ID:function:function1 \
    arn:aws:lambda:ap-northeast-1:$AWS_ACCOUNT_ID:function:function2 \
  --duration PT5M \
  --percentage 50
```

### S3ログ保存を有効化

```bash
export AWS_ACCOUNT_ID=`aws sts get-caller-identity --output text --query Account`
python create_experiment_template.py \
  --role-arn arn:aws:iam::$AWS_ACCOUNT_ID:role/FisLambdaExperimentRole \
  --lambda-arns arn:aws:lambda:ap-northeast-1:$AWS_ACCOUNT_ID:function:my-function \
  --log-bucket fis-test-lambda-$AWS_ACCOUNT_ID
```

## パラメータ

| パラメータ | 必須 | デフォルト | 説明 |
|-----------|------|-----------|------|
| `--role-arn` | ✓ | - | FISが使用するIAMロールのARN |
| `--lambda-arns` | ✓ | - | ターゲットLambda関数のARN（複数指定可） |
| `--description` | - | "Lambda fault injection experiment" | 実験の説明 |
| `--action-id` | - | `aws:fis:inject-api-unavailable-error` | FISアクションID |
| `--duration` | - | `PT2M` | 実験継続時間（ISO 8601形式） |
| `--percentage` | - | 100 | 影響を受けるターゲットの割合（0-100） |
| `--log-bucket` | - | - | ログ保存先S3バケット名 |
| `--region` | - | `ap-northeast-1` | AWSリージョン |
| `--no-start` | - | False | テンプレート作成のみ行い、実験は起動しない |

## 利用可能なFISアクション（Lambda用）

- `aws:fis:inject-api-unavailable-error`: API unavailableエラーを注入
- `aws:fis:inject-api-throttle-error`: APIスロットリングエラーを注入
- `aws:fis:inject-api-internal-error`: 内部エラーを注入

## 実験の監視

実験起動後、以下のコマンドでステータスを確認できます：

```bash
aws fis get-experiment --id <experiment-id>
```

または、AWSマネジメントコンソールの FIS ダッシュボードで確認できます。

## 実験の停止

実験を手動で停止する場合：

```bash
aws fis stop-experiment --id <experiment-id>
```

## トラブルシューティング

### エラー: "User: ... is not authorized to perform: fis:CreateExperimentTemplate"

IAMユーザー/ロールに `fis:CreateExperimentTemplate` 権限を追加してください。

### エラー: "Invalid IAM role ARN"

`--role-arn` で指定したIAMロールが存在し、FISサービスに信頼関係があることを確認してください。

### エラー: "Invalid resource ARN"

Lambda関数のARNが正しいこと、関数が存在することを確認してください。

## 参考資料

- [AWS FIS ドキュメント](https://docs.aws.amazon.com/fis/)
- [Boto3 FIS API リファレンス](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/fis.html)
- [Lambda障害注入の詳細](https://docs.aws.amazon.com/fis/latest/userguide/actions-aws-lambda.html)
