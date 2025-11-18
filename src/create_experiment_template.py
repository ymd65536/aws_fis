#!/usr/bin/env python3
"""
AWS FIS 実験テンプレート作成・起動スクリプト

このスクリプトは以下を実行します:
1. Lambda関数に障害を注入するFIS実験テンプレートを作成
2. 作成したテンプレートを使って実験を起動
"""
import argparse
import json
import sys
import boto3
from botocore.exceptions import ClientError


def create_experiment_template(
    client,
    description: str,
    role_arn: str,
    target_lambda_arns: list,
    action_id: str = "aws:lambda:invocation-error",
    duration: str = "PT2M",
    percentage: int = 100,
    log_bucket: str = None,
    log_prefix: str = "fis-logs"
):
    """
    FIS実験テンプレートを作成

    Args:
        client: boto3 FISクライアント
        description: 実験の説明
        role_arn: FISが使用するIAMロールARN
        target_lambda_arns: ターゲットLambda関数のARNリスト
        action_id: FISアクションID (デフォルト: Lambda API unavailableエラー注入)
        duration: 実験継続時間 (ISO 8601形式、デフォルト: 2分)
        percentage: 影響を受けるターゲットの割合 (デフォルト: 100%)
        log_bucket: CloudWatch Logs配信先のS3バケット名 (オプション)
        log_prefix: S3バケット内のプレフィックス (デフォルト: fis-logs)

    Returns:
        dict: 作成されたテンプレート情報
    """

    # ターゲット定義
    targets = {
        "lambda-functions": {
            "resourceType": "aws:lambda:function",
            "resourceArns": target_lambda_arns,
            "selectionMode": "ALL"
        }
    }

    # アクション定義
    actions = {
        "inject-fault": {
            "actionId": action_id,
            "parameters": {
                "duration": duration,
                "percentage": str(percentage)
            },
            "targets": {
                "Lambdas": "lambda-functions"
            }
        }
    }

    # 停止条件 (CloudWatch Alarmを使う場合)
    stop_conditions = [
        {
            "source": "none"
        }
    ]

    # テンプレート作成パラメータ
    template_params = {
        "description": description,
        "targets": targets,
        "actions": actions,
        "stopConditions": stop_conditions,
        "roleArn": role_arn,
        "tags": {
            "Environment": "test",
            "ManagedBy": "fis-automation"
        }
    }

    # ログ設定 (オプション)
    if log_bucket:
        template_params["logConfiguration"] = {
            "cloudWatchLogsConfiguration": {
                "logGroupArn": f"arn:aws:logs:{client.meta.region_name}:{boto3.client('sts').get_caller_identity()['Account']}:log-group:/aws/fis/*"
            },
            "s3Configuration": {
                "bucketName": log_bucket,
                "prefix": log_prefix
            },
            "logSchemaVersion": 1
        }

    try:
        response = client.create_experiment_template(**template_params)
        print(f"✓ 実験テンプレート作成成功")
        print(f"  Template ID: {response['experimentTemplate']['id']}")
        return response['experimentTemplate']
    except ClientError as e:
        print(f"✗ テンプレート作成失敗: {e}", file=sys.stderr)
        raise


def start_experiment(client, template_id: str, tags: dict = None):
    """
    FIS実験を起動

    Args:
        client: boto3 FISクライアント
        template_id: 実験テンプレートID
        tags: 実験に付与するタグ (オプション)

    Returns:
        dict: 起動された実験情報
    """

    params = {
        "experimentTemplateId": template_id,
        "tags": tags or {"StartedBy": "automation-script"}
    }

    try:
        response = client.start_experiment(**params)
        print(f"✓ 実験起動成功")
        print(f"  Experiment ID: {response['experiment']['id']}")
        print(f"  State: {response['experiment']['state']['status']}")
        return response['experiment']
    except ClientError as e:
        print(f"✗ 実験起動失敗: {e}", file=sys.stderr)
        raise


def get_experiment_status(client, experiment_id: str):
    """
    実験のステータスを取得

    Args:
        client: boto3 FISクライアント
        experiment_id: 実験ID

    Returns:
        dict: 実験情報
    """
    try:
        response = client.get_experiment(id=experiment_id)
        return response['experiment']
    except ClientError as e:
        print(f"✗ ステータス取得失敗: {e}", file=sys.stderr)
        raise


def main():
    parser = argparse.ArgumentParser(
        description="AWS FIS実験テンプレートの作成と起動"
    )
    parser.add_argument(
        "--role-arn",
        required=True,
        help="FISが使用するIAMロールのARN"
    )
    parser.add_argument(
        "--lambda-arns",
        required=True,
        nargs="+",
        help="ターゲットLambda関数のARN（スペース区切りで複数指定可）"
    )
    parser.add_argument(
        "--description",
        default="Lambda fault injection experiment",
        help="実験の説明"
    )
    parser.add_argument(
        "--action-id",
        default="aws:fis:inject-api-unavailable-error",
        help="FISアクションID"
    )
    parser.add_argument(
        "--duration",
        default="PT2M",
        help="実験継続時間 (ISO 8601形式、例: PT2M = 2分)"
    )
    parser.add_argument(
        "--percentage",
        type=int,
        default=100,
        help="影響を受けるターゲットの割合 (0-100)"
    )
    parser.add_argument(
        "--log-bucket",
        help="ログ保存先S3バケット名 (オプション)"
    )
    parser.add_argument(
        "--region",
        default="us-east-1",
        help="AWSリージョン (デフォルト: us-east-1)"
    )
    parser.add_argument(
        "--no-start",
        action="store_true",
        help="テンプレート作成のみ行い、実験は起動しない"
    )

    args = parser.parse_args()

    # FISクライアント作成
    client = boto3.client('fis', region_name=args.region)

    print("=== AWS FIS 実験テンプレート作成 ===")
    print(f"ターゲット Lambda ARNs: {args.lambda_arns}")
    print(f"アクション: {args.action_id}")
    print(f"継続時間: {args.duration}")
    print(f"影響率: {args.percentage}%")
    print()

    # 実験テンプレート作成
    template = create_experiment_template(
        client=client,
        description=args.description,
        role_arn=args.role_arn,
        target_lambda_arns=args.lambda_arns,
        action_id=args.action_id,
        duration=args.duration,
        percentage=args.percentage,
        log_bucket=args.log_bucket
    )

    template_id = template['id']
    print(f"\nテンプレート詳細:")
    print(json.dumps(template, indent=2, default=str))

    # 実験起動 (--no-start が指定されていない場合)
    if not args.no_start:
        print("\n=== 実験起動 ===")
        experiment = start_experiment(
            client=client,
            template_id=template_id,
            tags={"CreatedBy": "fis-script"}
        )

        print(f"\n実験詳細:")
        print(json.dumps(experiment, indent=2, default=str))
        print(f"\n実験を監視するには:")
        print(f"  aws fis get-experiment --id {experiment['id']}")
    else:
        print(f"\n実験を起動するには:")
        print(f"  python {__file__} start --template-id {template_id}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
